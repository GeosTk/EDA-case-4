"""Validate geometry, provenance, programme constraints and submission artifacts."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import pandas as pd
from pypdf import PdfReader
import nbformat
from analyse import district_join

ROOT = Path(__file__).resolve().parents[1]


def run():
    # Website application bundles can embed service tokens. Publish analytical
    # resources and provenance without accidentally redistributing those tokens.
    service_token = re.compile(rb'(?:pk|sk)\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
    findings = []
    for folder in ['data', 'docs', 'src', 'outputs', 'report', 'notebooks']:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                if service_token.search(path.read_bytes()):
                    findings.append(str(path.relative_to(ROOT)))
    assert not findings, 'Embedded service token found in: '+', '.join(findings)
    # Nontrivial synthetic geometry: an exterior, a hole, an island, and outside.
    boundaries = [{'properties': {'district': 'Example'}, 'geometry': {'type':'MultiPolygon',
        'coordinates':[[[[0,0],[4,0],[4,4],[0,4],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]],
                       [[[6,6],[7,6],[7,7],[6,7],[6,6]]]]}}]
    actual = district_join(np.array([[.5,.5],[1.5,1.5],[6.5,6.5],[9,9]]), boundaries)
    assert actual.tolist() == ['Example','','Example',''], actual
    manifest = [json.loads(line) for line in (ROOT/'data/download_manifest.jsonl').read_text().splitlines()]
    latest = {entry['file']:entry for entry in manifest}
    for file, entry in latest.items():
        p = ROOT/file
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == entry['sha256'], file
    raw_files = {str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/raw').iterdir() if p.is_file()}
    assert raw_files.issubset(latest), 'Untracked raw source provenance: '+str(raw_files-set(latest))
    summary = json.loads((ROOT/'outputs/summary.json').read_text())
    config = json.loads((ROOT/'config.json').read_text())
    audit = pd.read_csv(ROOT/'outputs/facility_audit.csv')
    eligible = pd.read_csv(ROOT/'outputs/eligible_facilities.csv')
    funded = pd.read_csv(ROOT/'outputs/funded_facilities.csv')
    ranking = pd.read_csv(ROOT/'outputs/district_ranking.csv')
    budget = pd.read_csv(ROOT/'outputs/budget.csv')
    costs = pd.read_csv(ROOT/'outputs/cost_sensitivity.csv')
    assert len(audit) == summary['source_facilities'] and audit.id.is_unique
    assert len(eligible) == summary['eligible_facilities']
    assert ranking['rank'].tolist() == list(range(1,len(ranking)+1))
    assert ranking.unserved_candidates.sum() == len(eligible)
    assert np.isclose(ranking.priority_sum.sum(), eligible.priority_score.sum())
    assert set(funded.id).issubset(eligible.id) and funded.id.is_unique
    assert funded.ELECTRIFIC.eq('No').all() and funded.ELECTRICIT.eq('No').all()
    assert funded.ERT_status.eq('No').all() and funded.imputed_fields.isna().all()
    assert funded.installation_usd.sum() == summary['installation_usd']
    assert budget.usd.sum() == config['budget_usd']
    assert summary['contingency_usd'] >= config['minimum_contingency_usd']
    assert funded.groupby('district').size().max() <= config['maximum_facilities_per_district']
    assert funded.loc[funded.remote,'installation_usd'].sum() >= config['installation_budget_usd']*config['minimum_remote_installation_share']
    assert np.isclose(funded.catchment_5km.sum(), summary['modelled_people_5km'])
    assert (funded.catchment_3km <= funded.catchment_5km+1e-6).all()
    assert (funded.catchment_5km <= funded.catchment_10km+1e-6).all()
    assert costs.facilities.is_monotonic_decreasing
    assert costs.contingency_usd.ge(config['minimum_contingency_usd']).all()
    assert len(PdfReader(ROOT/'report/case_study_4_report.pdf').pages) == 4
    nb = nbformat.read(ROOT/'notebooks/healthcare_electrification.ipynb', as_version=4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == 'code']
    assert code and all(c.execution_count is not None for c in code), 'Notebook is not fully executed'
    assert not [o for c in code for o in c.outputs if o.output_type == 'error'], 'Notebook contains errors'
    print(f'PASS: geometry including holes/islands; {len(raw_files)} live-source checksums; '
          f'{len(audit):,} source records; {len(eligible)} eligible; {len(funded)} awards; '
          f'USD {budget.usd.sum():,}; protected remote/maintenance reserves; '
          f'catchment conservation; price sensitivity; four PDF pages; {len(code)} executed notebook cells.')


if __name__ == '__main__':
    run()
