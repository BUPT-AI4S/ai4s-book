"""Record actual launch and content-release times for the book homepage."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def write_homepage_dates(root, metadata):
    path = Path(root) / 'index.html'
    if not path.is_file():
        return
    html = path.read_text(encoding='utf-8')
    for identity, key in [('first-published', 'firstPublishedAt'), ('last-updated', 'lastUpdatedAt')]:
        value = metadata[key]
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        display = date.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        html, count = re.subn(r'<time id="' + identity + r'"[^>]*>[^<]*</time>',
                             f'<time id="{identity}" datetime="{value}">{display}</time>', html)
        if count != 1:
            raise ValueError(f'Missing unique homepage date: {identity}')
    version = re.sub(r'\D', '', metadata['lastUpdatedAt'].split('+')[0])
    html = re.sub(r'(src="static/js/home\.mjs)(?:\?[^\"]*)?(")',
                  lambda match: match[1] + '?v=release-' + version + match[2], html)
    path.write_text(html, encoding='utf-8', newline='\n')


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
    write_homepage_dates(root, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first-published', help='First successful Pages deployment time, for initial setup only')
    args = parser.parse_args()
    print(json.dumps(update(args.first_published)))
