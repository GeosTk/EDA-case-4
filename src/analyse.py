"""Fresh national analysis using ONLY resources downloaded from live EAE endpoints.

The index is an explicit facility-screening extension, not a reconstruction of
EAE's browser state or a claim that the website produced our facility score.
"""
from pathlib import Path
import json
import hashlib
import importlib.metadata as metadata
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform, transform_geom
from rasterio.features import rasterize
from scipy.spatial import cKDTree
from matplotlib.path import Path as PolygonPath

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'outputs'


def district_join(xy, features):
    """Exact point-in-polygon match in WGS84, preserving holes and islands."""
    names = np.full(len(xy), '', dtype=object)
    for feature in features:
        geometry = feature['geometry']
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        for polygon in polygons:
            exterior = np.asarray(polygon[0])
            lo, hi = exterior.min(axis=0), exterior.max(axis=0)
            candidates = np.flatnonzero(((xy >= lo) & (xy <= hi)).all(axis=1))
            if not len(candidates):
                continue
            inside = PolygonPath(exterior).contains_points(xy[candidates], radius=1e-10)
            for hole in polygon[1:]:
                inside &= ~PolygonPath(np.asarray(hole)).contains_points(xy[candidates])
            names[candidates[inside]] = feature['properties']['district']
    return names


def sample_layer(name, xy):
    with rasterio.open(RAW/name) as src:
        x, y = transform('EPSG:4326', src.crs, xy[:, 0].tolist(), xy[:, 1].tolist())
        samples = list(src.sample(zip(x, y), indexes=1, masked=True))
        values = np.array([np.nan if np.ma.is_masked(v[0]) else float(v[0]) for v in samples])
        return values, {'file': name, 'crs': str(src.crs), 'shape': list(src.shape),
                        'nodata': src.nodata, 'pixel_width_m': src.transform.a,
                        'pixel_height_m': -src.transform.e, 'bands': src.count,
                        'sample_missing': int(np.isnan(values).sum())}


def catchments(xy, boundaries, radii=(3, 5, 10)):
    """Allocate each positive population cell to its nearest facility, once.

    Use all 4,938 facilities, including private and electrified alternatives.
    Co-located facilities share their assigned cells equally. Radius is straight
    line in EPSG:3857, not travel time, utilisation, or a clinical service boundary.
    """
    with rasterio.open(RAW/'population.tif') as src:
        population = src.read(1, masked=True)
        shapes = [(transform_geom('EPSG:4326', src.crs, f['geometry']), 1) for f in boundaries]
        country = rasterize(shapes, out_shape=src.shape, transform=src.transform, fill=0, dtype='uint8')
        valid = (~np.ma.getmaskarray(population)) & (country > 0) & (population.data > 0)
        row, col = np.where(valid)
        px, py = rasterio.transform.xy(src.transform, row, col)
        weights = population.data[valid].astype(float)
        fx, fy = transform('EPSG:4326', src.crs, xy[:, 0].tolist(), xy[:, 1].tolist())
    # Rounding only defines identical locations at centimetre precision.
    unique, inverse, multiplicity = np.unique(np.round(np.c_[fx, fy], 2), axis=0, return_inverse=True, return_counts=True)
    distances, nearest = cKDTree(unique).query(np.c_[px, py], k=1)
    result = {}
    for radius in radii:
        selected = distances <= radius*1000
        assigned = np.bincount(nearest[selected], weights=weights[selected], minlength=len(unique))
        result[radius] = assigned[inverse]/multiplicity[inverse]
        assert np.isclose(result[radius].sum(), weights[selected].sum())
    audit = {'population_in_country_cells': float(weights.sum()), 'positive_country_cells': int(valid.sum()),
             'facilities': len(xy), 'unique_coordinate_groups': len(unique),
             'co_located_facility_records': int(sum(multiplicity[multiplicity > 1])),
             'population_assigned_within_5km': float(result[5].sum()),
             'population_beyond_5km': float(weights[distances > 5000].sum()),
             'method': 'Nearest facility; one allocation per cell; co-locations share equally; centroid distance'}
    return result, audit


def score(frame, config, weights=None):
    result = frame.copy()
    weights = weights or config['weights']
    pop_cap = float(np.percentile(result['catchment_5km'], 95))
    energy_cap = float(np.percentile(result['daily_kwh'], 95))
    result['population_component'] = (np.log1p(result['catchment_5km'])/np.log1p(pop_cap)).clip(0, 1)
    result['clinical_energy_component'] = (np.log1p(result['daily_kwh'])/np.log1p(energy_cap)).clip(0, 1)
    result['distance_component'] = (result['line_km']/config['distance_score_cap_km']).clip(0, 1)
    # Fixed national RWI anchor; higher score denotes lower relative wealth.
    result['poverty_component'] = ((2-result['rwi'])/4).clip(0, 1)
    result['priority_score'] = sum(result[key+'_component']*value for key, value in weights.items())
    result.attrs['normalization'] = {'population_95th_percentile': pop_cap, 'daily_kwh_95th_percentile': energy_cap}
    return result


def district_ranking(frame):
    result = frame.groupby('district').agg(
        unserved_candidates=('id', 'size'), priority_sum=('priority_score', 'sum'),
        mean_priority=('priority_score', 'mean'), catchment_people=('catchment_5km', 'sum'),
        daily_kwh=('daily_kwh', 'sum'), median_line_km=('line_km', 'median'),
        mean_rwi=('rwi', 'mean'), median_ghi=('ghi', 'median'),
        remote_candidates=('remote', 'sum')).reset_index()
    result = result.sort_values(['priority_sum', 'catchment_people', 'district'], ascending=[False, False, True]).reset_index(drop=True)
    result.insert(0, 'rank', np.arange(1, len(result)+1))
    return result


def portfolio(frame, ranked_districts, config, multiplier=1.0, value_first=False):
    """Seed the top five districts, reserve remote investment nationally, then
    fill by priority within the top five and finally across remaining districts.
    """
    focus = ranked_districts.head(config['districts_to_fund'])['district'].tolist()
    candidates = frame.copy()
    candidates['installation_usd'] = (candidates['base_installation_usd']*multiplier).round().astype(int)
    candidates['value_score'] = candidates['catchment_5km']/candidates['installation_usd']
    order = ['value_score', 'priority_score', 'id'] if value_first else ['priority_score', 'catchment_5km', 'id']
    candidates = candidates.sort_values(order, ascending=[False, False, True])
    chosen, remaining, district_counts = [], config['installation_budget_usd'], {}

    def add(row):
        nonlocal remaining
        if row['id'] in chosen or row['installation_usd'] > remaining:
            return False
        if district_counts.get(row['district'], 0) >= config['maximum_facilities_per_district']:
            return False
        chosen.append(row['id'])
        district_counts[row['district']] = district_counts.get(row['district'], 0)+1
        remaining -= row['installation_usd']
        return True

    for district in focus:
        options = candidates[candidates.district.eq(district)]
        if len(options):
            add(options.iloc[0])
    remote_target = config['installation_budget_usd']*config['minimum_remote_installation_share']
    remote_spend = candidates[candidates.id.isin(chosen) & candidates.remote]['installation_usd'].sum()
    if not value_first:
        for _, row in candidates[candidates.remote].iterrows():
            if remote_spend >= remote_target:
                break
            if add(row):
                remote_spend += row['installation_usd']
    for _, row in candidates[candidates.district.isin(focus)].iterrows():
        add(row)
    for _, row in candidates.iterrows():
        add(row)
    selected = candidates[candidates.id.isin(chosen)].copy()
    assert selected.id.is_unique
    assert selected.installation_usd.sum() <= config['installation_budget_usd']
    assert selected.groupby('district').size().max() <= config['maximum_facilities_per_district']
    if not value_first:
        assert selected.loc[selected.remote, 'installation_usd'].sum() >= remote_target
    return selected.sort_values(['district', 'priority_score'], ascending=[True, False])


def run():
    OUT.mkdir(exist_ok=True)
    config = json.loads((ROOT/'config.json').read_text())
    facilities = json.loads((RAW/'health-facilities.geojson').read_text())['features']
    boundaries = json.loads((RAW/'districts.geojson').read_text())['features']
    xy = np.array([f['geometry']['coordinates'][:2] for f in facilities])
    frame = pd.DataFrame([f['properties'] for f in facilities])
    assert frame.id.is_unique and len(facilities) > 0
    assert np.isfinite(xy).all() and (np.abs(xy[:,0]) <= 180).all() and (np.abs(xy[:,1]) <= 90).all()
    frame['longitude'], frame['latitude'] = xy[:, 0], xy[:, 1]
    frame['district_source'] = frame['DISTRICT']
    frame['district'] = district_join(xy, boundaries)
    frame['boundary_unmatched'] = frame.district.eq('')
    # Retain unmatched records in the audit; missing boundary joins are excluded
    # from district investment ranking, not silently assigned to old boundaries.
    raster_metadata = []
    for field, filename in [('line_km', 'distribution-distance.tif'), ('rwi', 'wealth.tif'), ('ghi', 'solar-ghi.tif')]:
        frame[field], info = sample_layer(filename, xy)
        raster_metadata.append(info)
    populations, catchment_audit = catchments(xy, boundaries)
    for radius, values in populations.items():
        frame[f'catchment_{radius}km'] = values
    frame['daily_kwh'] = pd.to_numeric(frame['Av_kWh_d'], errors='coerce')
    frame['remote'] = frame.line_km.gt(config['remote_distance_km'])
    base_filter = frame.OWNERSHIP.eq('GOVT') & frame.LEVEL.isin(['HC II', 'HC III']) & frame.ELECTRIFIC.eq('No')
    candidate_filter = base_filter & frame.ELECTRICIT.eq('No') & frame.ERT_status.eq('No') & ~frame.boundary_unmatched
    eligible = frame[candidate_filter].copy()
    missing = eligible[['line_km', 'rwi', 'ghi', 'daily_kwh']].isna()
    eligible['imputed_fields'] = missing.apply(lambda row: ','.join(row.index[row]), axis=1)
    for field in ['line_km', 'rwi', 'ghi', 'daily_kwh']:
        eligible[field] = eligible[field].fillna(eligible[field].median())
    eligible['remote'] = eligible.line_km.gt(config['remote_distance_km'])
    # Solar resource is retained as a feasibility check, not a reason to divert
    # assistance from poorer or cloudier places. Annual means do not size storage.
    eligible['base_installation_usd'] = np.where(eligible.LEVEL.eq('HC II'), config['hc_ii_critical_system_usd'], config['hc_iii_critical_system_usd'])
    eligible['base_installation_usd'] = (eligible.base_installation_usd*np.where(eligible.remote, config['remote_cost_multiplier'], 1)).astype(int)
    scored = score(eligible, config)
    normalization = scored.attrs['normalization']
    ranked = district_ranking(scored)
    funded = portfolio(scored, ranked, config)
    installation = int(funded.installation_usd.sum())
    contingency = config['budget_usd']-installation-config['audit_usd']-config['five_year_maintenance_usd']
    budget = pd.DataFrame([
        {'item': 'Installed critical-service systems', 'usd': installation},
        {'item': 'Audits, design and duplicate-funding checks', 'usd': config['audit_usd']},
        {'item': 'Five-year maintenance reserve', 'usd': config['five_year_maintenance_usd']},
        {'item': 'Contingency and unallocated installation balance', 'usd': contingency}])
    assert budget.usd.sum() == config['budget_usd'] and contingency >= config['minimum_contingency_usd']
    cost_sensitivity = []
    for multiplier in [.8, 1, 1.2, 1.4]:
        p = portfolio(scored, ranked, config, multiplier)
        cost_sensitivity.append({'cost_change_pct': round((multiplier-1)*100), 'facilities': len(p),
            'installation_usd': int(p.installation_usd.sum()), 'modelled_people': round(p.catchment_5km.sum()),
            'contingency_usd': int(config['budget_usd']-p.installation_usd.sum()-config['audit_usd']-config['five_year_maintenance_usd']),
            'district_allocation': '; '.join(f'{name}: {len(group)}' for name,group in p.groupby('district'))})
    weight_sensitivity = []
    policies = {'Baseline': config['weights'],
                'More population': {'population': .65, 'clinical_energy': .15, 'distance': .10, 'poverty': .10},
                'More equity': {'population': .25, 'clinical_energy': .15, 'distance': .40, 'poverty': .20}}
    for name, weights in policies.items():
        ranked_variant = district_ranking(score(eligible, config, weights))
        weight_sensitivity.append({'policy': name, 'weights': json.dumps(weights),
                                  'top_five': '; '.join(ranked_variant.head(5).district)})
    value_portfolio = portfolio(scored, ranked, config, value_first=True)
    district_funding = funded.groupby('district').agg(facilities=('id', 'size'), installation_usd=('installation_usd', 'sum'),
        modelled_people=('catchment_5km', 'sum'), remote_facilities=('remote', 'sum'), hc_iii=('LEVEL', lambda x:int(x.eq('HC III').sum()))).reset_index()
    district_funding['installation_usd_per_modelled_person'] = district_funding.installation_usd/district_funding.modelled_people
    cols = ['id','FACILITY_N','LEVEL','district','district_source','ELECTRIFIC','ELECTRICIT','ERT_status','latitude','longitude',
            'daily_kwh','catchment_3km','catchment_5km','catchment_10km','line_km','rwi','ghi','remote',
            'population_component','clinical_energy_component','distance_component','poverty_component', 'priority_score','imputed_fields','base_installation_usd']
    frame.to_csv(OUT/'facility_audit.csv', index=False)
    scored[cols].sort_values('priority_score', ascending=False).to_csv(OUT/'eligible_facilities.csv', index=False)
    ranked.to_csv(OUT/'district_ranking.csv', index=False)
    funded[cols+['installation_usd']].to_csv(OUT/'funded_facilities.csv', index=False)
    value_portfolio[cols+['installation_usd']].to_csv(OUT/'value_first_facilities.csv', index=False)
    district_funding.to_csv(OUT/'district_budget.csv', index=False)
    budget.to_csv(OUT/'budget.csv', index=False)
    pd.DataFrame(cost_sensitivity).to_csv(OUT/'cost_sensitivity.csv', index=False)
    pd.DataFrame(weight_sensitivity).to_csv(OUT/'weight_sensitivity.csv', index=False)
    pd.DataFrame(raster_metadata).to_json(OUT/'raster_metadata.json', orient='records', indent=2)
    (OUT/'catchment_audit.json').write_text(json.dumps(catchment_audit, indent=2)+'\n')
    total_people = float(funded.catchment_5km.sum())
    summary = {'data_source': 'Fresh live EAE API and EAE-linked public storage; no previous local exports',
        'source_facilities': len(frame), 'source_electricity_status': frame.ELECTRIFIC.value_counts().to_dict(),
        'public_unserved_hc_ii_iii_before_exclusions': int(base_filter.sum()),
        'eligible_facilities': len(scored), 'eligible_districts': len(ranked),
        'ert_flagged_in_base_filter': int((base_filter & ~frame.ERT_status.eq('No')).sum()),
        'base_filter_boundary_unmatched': int((base_filter & frame.boundary_unmatched).sum()),
        'all_boundary_unmatched': int(frame.boundary_unmatched.sum()),
        'eligible_with_imputation': int(scored.imputed_fields.ne('').sum()),
        'normalization': normalization, 'top_five': ranked.head(5).district.tolist(),
        'funded_facilities': len(funded), 'installation_usd': installation, 'contingency_usd': contingency,
        'modelled_people_3km': float(funded.catchment_3km.sum()), 'modelled_people_5km': total_people,
        'modelled_people_10km': float(funded.catchment_10km.sum()),
        'full_budget_usd_per_modelled_person': config['budget_usd']/total_people,
        'remote_facilities_funded': int(funded.remote.sum()), 'remote_installation_usd': int(funded.loc[funded.remote,'installation_usd'].sum()),
        'hc_iii_funded': int(funded.LEVEL.eq('HC III').sum()),
        'value_first_facilities': len(value_portfolio), 'value_first_modelled_people': float(value_portfolio.catchment_5km.sum()),
        'value_first_remote_facilities': int(value_portfolio.remote.sum()),
        'maintenance_per_facility_per_year_usd': config['five_year_maintenance_usd']/len(funded)/5,
        'clinical_energy_kwh_day_funded': float(funded.daily_kwh.sum()),
        'funded_ghi_min': float(funded.ghi.min()), 'funded_ghi_max': float(funded.ghi.max()),
        'versions': {p:metadata.version(p) for p in ['numpy','pandas','scipy','rasterio','matplotlib']}}
    assert sum(config['weights'].values()) == 1
    assert np.isfinite(scored.priority_score).all() and scored.priority_score.between(0, 1).all()
    assert funded.catchment_5km.sum() <= catchment_audit['population_assigned_within_5km']
    assert funded.remote.sum() > 0
    (OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    manifest = [{'file': str(p.relative_to(ROOT)).replace('\\','/'), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                 'bytes': p.stat().st_size} for p in sorted(RAW.iterdir()) if p.is_file()]
    pd.DataFrame(manifest).to_csv(OUT/'source_checksums.csv', index=False)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    run()
