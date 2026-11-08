"""Download public EAE resources with URL, retrieval time and SHA-256 provenance."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from datetime import datetime, timezone
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'www.energyaccessexplorer.org', 'api.energyaccessexplorer.org',
           'world.energyaccessexplorer.org', 'wri-public-data.s3.amazonaws.com'}


def fetch(url, filename):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED:
        raise ValueError('Only official HTTPS EAE resource hosts are allowed')
    dest = (ROOT / 'data/raw' / filename).resolve()
    dest.relative_to((ROOT / 'data/raw').resolve())
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={'User-Agent': 'EDA-case-4 academic research', 'Accept': '*/*'})
    with urlopen(request, timeout=60) as response:
        data = response.read()
        content_type = response.headers.get('Content-Type')
    dest.write_bytes(data)
    record = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
              'file': str(dest.relative_to(ROOT)).replace('\\', '/'),
              'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
              'content_type': content_type}
    with (ROOT / 'data/download_manifest.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    if len(sys.argv) < 3 or len(sys.argv) % 2 != 1:
        raise SystemExit('Usage: python src/fetch_eae.py URL FILENAME [URL FILENAME ...]')
    for i in range(1, len(sys.argv), 2):
        fetch(sys.argv[i], sys.argv[i+1])
