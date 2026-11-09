"""Verify native EAE files without modifying their original bytes."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'data/native_exports/assistance_need'
PACKAGE = DIRECTORY/'202611091724-eae-export.zip'
EXPECTED_PACKAGE_SHA = '29f60e2071b7fdfc8b52f8729c059bb44126bbfbbb5cfcd467b495719cd3c515'


def run():
    actual_sha = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    assert actual_sha == EXPECTED_PACKAGE_SHA, 'Original EAE package changed'
    expected = {'eae-summary.pptx', 'eae-assistance-need-index-map.tif',
                'eae-assistance-need-index-high-priority-areas.csv', 'eae-population-area-share.csv'}
    files = []
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == expected
        for name in sorted(expected):
            data = archive.read(name)
            assert data == (DIRECTORY/name).read_bytes(), 'Extracted file changed: '+name
            files.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    with (DIRECTORY/'eae-assistance-need-index-high-priority-areas.csv').open(newline='',encoding='utf-8-sig') as f:
        districts = list(csv.DictReader(f))
    assert len(districts) == len({r['District'] for r in districts}) == 146
    top_ten = [r['District'] for r in districts[:10]]
    assert top_ten == ['Wakiso','Kampala','Amudat','Buvuma','Kasese','Lamwo','Obongi','Kalangala','Pakwach','Terego']
    assert all(all(v is not None and v != '' for v in r.values()) for r in districts)
    assert all(0 <= float(r['Priority score'].rstrip('%')) <= 100 for r in districts)
    with (DIRECTORY/'eae-population-area-share.csv').open(newline='',encoding='utf-8-sig') as f:
        next(f)
        shares = list(csv.DictReader(f))
    selected = [r for r in shares if r['Level'] != 'outside the analysis']
    area = sum(int(r['Assistance Need Index (1km²)']) for r in selected)
    population = sum(int(r['Assistance Need Index (people)']) for r in selected)
    population_with_outside = sum(int(r['Assistance Need Index (people)']) for r in shares)
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    token = re.compile(rb'(?:pk|sk)\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
    with zipfile.ZipFile(DIRECTORY/'eae-summary.pptx') as ppt:
        assert ppt.testzip() is None
        slides = [n for n in ppt.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        assert len(slides) == 15
        assert not any(token.search(ppt.read(n)) for n in ppt.namelist()), 'Embedded service token in native presentation'
        settings = {}
        for name in ['ppt/slides/slide6.xml', 'ppt/slides/slide7.xml']:
            root = ET.fromstring(ppt.read(name))
            for row in root.findall('.//a:tr', ns):
                cells = [' '.join(t.text or '' for t in c.findall('.//a:t', ns)) for c in row.findall('a:tc',ns)]
                if cells and cells[0] != 'Dataset':
                    settings[cells[0]] = {'native_unit_label':cells[1], 'domain':cells[2],
                                         'selected_range':cells[3], 'importance':int(cells[4])}
        expected_weights = {'Population Count':5,'Relative Wealth Index':4,'Health facilities':5,
                            'Global Horizontal Irradiation':1,'Distribution Lines':4}
        assert {k:v['importance'] for k,v in settings.items()} == expected_weights
        assert settings['Health facilities']['selected_range'].endswith('max: 5')
    with rasterio.open(DIRECTORY/'eae-assistance-need-index-map.tif') as src:
        raster = src.read(1,masked=True)
        raster_info = {'shape':list(src.shape), 'crs':str(src.crs),'nodata':src.nodata,
                       'valid_cells':int(raster.count()),'minimum':float(raster.min()),'maximum':float(raster.max())}
        assert src.nodata == 255 and raster_info['valid_cells'] == 127414
        assert raster_info['minimum'] >= 0 and raster_info['maximum'] <= 254
    manifest = {'source': 'Signed-in Energy Access Explorer native Download all (.zip) action',
        'analysis_url': 'https://www.energyaccessexplorer.org/tool/a/?id=5d137d39-e46d-4abc-bfc9-76254501fa09',
        'export_date_local': '2026-11-09', 'export_filename_time_zone':'Africa/Johannesburg',
        'downloaded_file_mtime_utc':datetime.fromtimestamp(PACKAGE.stat().st_mtime,timezone.utc).isoformat(),
        'verified_at_utc':datetime.now(timezone.utc).isoformat(), 'geography':'Uganda', 'analysis_area':'District',
        'selected_index':'Assistance Need Index', 'package_file':'assistance_need/'+PACKAGE.name,
        'package_sha256':actual_sha, 'package_bytes':PACKAGE.stat().st_size,'original_files':files,
        'district_rows':len(districts),'slide_count':len(slides),'native_top_ten':top_ten,
        'native_presentation_settings':settings,'native_raster':raster_info,
        'area_share_selected_total':area,'selected_population':population,
        'population_total_with_outside':population_with_outside,
        'displayed_population_total':46050198,
        'purpose':'Supplemental native EAE evidence collected after the original independent facility-based analysis',
        'interpretation_guide':'README.md'}
    (ROOT/'data/native_exports/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'PASS: unchanged original ZIP and four extracted members; {len(districts)} districts; '
          f'{len(slides)} native slides; expected weights and healthcare range; TIFF valid cells {raster_info["valid_cells"]}; no embedded service tokens')


if __name__ == '__main__':
    run()
