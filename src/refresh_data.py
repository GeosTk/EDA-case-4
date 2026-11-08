"""Refresh the six analytical layers through the live public EAE catalogue."""
import json
from fetch_eae import fetch, ROOT

GEOGRAPHY = '5d137d39-e46d-4abc-bfc9-76254501fa09'
LAYERS = {
    '6adb67b1-b116-4be6-aad5-c6cc6708a7cf': ('vectors', 'health-facilities.geojson'),
    'd461659b-af30-4b71-84ed-24c8e5bbffa9': ('vectors', 'districts.geojson'),
    'e3ed524b-d372-43a5-9086-55ec0aa86208': ('raster', 'distribution-distance.tif'),
    '45ada3b1-dba0-4a2b-86fc-3cb99458a235': ('raster', 'wealth.tif'),
    'bab58981-6a6f-4f6f-855d-4c4ae42bddf8': ('raster', 'solar-ghi.tif'),
    '2d03d527-6679-4f80-9f31-ca241e3b0dc5': ('raster', 'population.tif'),
}


if __name__ == '__main__':
    fetch(f'https://api.energyaccessexplorer.org/geographies?id=eq.{GEOGRAPHY}', 'uganda-geographies.json')
    fetch(f'https://api.energyaccessexplorer.org/datasets?geography_id=eq.{GEOGRAPHY}', 'uganda-datasets.json')
    datasets = json.loads((ROOT/'data/raw/uganda-datasets.json').read_text())
    lookup = {d['id']: d for d in datasets}
    for dataset_id, (function, filename) in LAYERS.items():
        endpoint = next(f['endpoint'] for f in lookup[dataset_id]['processed_files'] if f['func'] == function)
        fetch(endpoint, filename)
    print('Fresh analytical snapshot saved. Re-run analyse.py and review the report narrative.')
