"""Bundle the exact live EAE downloads used by this analysis, with provenance."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]

README = '''EAE source downloads supporting Case Study 4

This package contains the exact nine resources downloaded from the live Energy
Access Explorer API and its linked public storage for the analysis. Their UTC
retrieval timestamps, URLs and SHA-256 hashes are in download_manifest.jsonl.

Contents
  raw/health-facilities.geojson       National facility points and attributes
  raw/districts.geojson               District boundaries
  raw/population.tif                  Population raster
  raw/distribution-distance.tif       Proximity to distribution infrastructure
  raw/wealth.tif                      Relative wealth raster
  raw/solar-ghi.tif                   Solar-resource raster
  raw/uganda-datasets.json            Source metadata, vintages and licences
  raw/uganda-geographies.json         Geography definitions
  raw/selected-categories.json        Layer units and native analysis definitions
  download_manifest.jsonl             Exact download provenance
  sources.json                       Attribution and cost-source interpretation

Export status
These are raw EAE source downloads. The website's native analysis-export package
(PowerPoint, priority CSVs and index TIFF) requires EAE account sign-in and was
not an input to the reported funding ranking. The final ranking, named awards
and sensitivity tables are independent calculations provided in outputs/ in
the repository. They must not be described as EAE-generated district ANI data.
The supplemental native EAE export was subsequently collected on 9 November
2026 and is provided separately under data/native_exports/ in the repository.

Reproducibility
https://github.com/GeosTk/EDA-case-4
Run src/analyse.py using the supplied source snapshot and config.json.
The report explains the distinction between website exploration and the
facility-specific scoring extension. Original data-owner terms apply; see
raw/uganda-datasets.json and sources.json.
'''


def run():
    manifest_path = ROOT/'data/download_manifest.jsonl'
    entries = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    target = ROOT/'data/eae_source_downloads.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            path = ROOT/entry['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], entry['file']
            archive.write(path, 'raw/'+path.name)
        archive.write(manifest_path, 'download_manifest.jsonl')
        archive.write(ROOT/'docs/sources.json', 'sources.json')
        archive.writestr('README.txt', README)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for entry in entries:
            data = archive.read('raw/'+Path(entry['file']).name)
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
    print(f'Verified {len(entries)} original EAE resources in {target} ({target.stat().st_size:,} bytes)')


if __name__ == '__main__':
    run()
