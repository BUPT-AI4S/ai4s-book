"""Record actual launch and content-release times for the book homepage."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def update(first_published=None, root=ROOT):
    root = Path(root)
    path = root / 'data/site-meta.json'
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    first = previous.get('firstPublishedAt') or first_published
    if not first or datetime.fromisoformat(first.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('An actual timezone-aware first publication time is required')
    if previous.get('firstPublishedAt') and first_published and first != first_published:
        raise ValueError('The first publication time must remain unchanged')
    catalog = json.loads((root / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
    result = dict(schemaVersion=1, firstPublishedAt=first,
                  lastUpdatedAt=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  sourceCommit=catalog['sourceCommit'], displayTimezone='Asia/Shanghai')
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first-published', help='First successful Pages deployment time, for initial setup only')
    args = parser.parse_args()
    print(json.dumps(update(args.first_published)))
