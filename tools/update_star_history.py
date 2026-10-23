"""Generate the README Star History chart from the repository's GitHub data."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'BUPT-AI4S/ai4s-book'


def fetch_project(token):
    def get(path, accept='application/vnd.github+json'):
        request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
            headers={'Authorization': 'Bearer ' + token, 'Accept': accept, 'User-Agent': 'AI4SBook-Star-History'})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    repository = get('')
    stars = []
    for page in range(1, 1001):
        values = get(f'/stargazers?per_page=100&page={page}', 'application/vnd.github.star+json')
        stars.extend(item['starred_at'] for item in values)
        if len(values) < 100:
            break
    return dict(repository=REPOSITORY, createdAt=repository['created_at'],
                observedAt=datetime.now(timezone.utc).isoformat(), starCount=repository['stargazers_count'], starredAt=sorted(stars))


def moment(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def chart(project, dark=False):
    background, ink, grid = ('#101820', '#e8eef6', '#293848') if dark else ('#ffffff', '#182536', '#e8edf3')
    start, end = moment(project['createdAt']), moment(project['observedAt'])
    end = max(end, start + 3600)
    stars = sorted(moment(value) for value in project['starredAt'])
    ymax = max(1, math.ceil(max(len(stars), project['starCount']) / 4) * 4)
    x = lambda value: 85 + (value - start) / (end - start) * 750
    y = lambda value: 352 - value / ymax * 245
    points = [(start, 0), *((value, index + 1) for index, value in enumerate(stars)), (end, len(stars))]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="440" viewBox="0 0 900 440" role="img" aria-labelledby="title description">',
             '<title id="title">Star History · BUPT-AI4S/ai4s-book</title>',
             f'<desc id="description">GitHub star history, {project["starCount"]} stars at {escape(project["observedAt"])}</desc>',
             f'<rect width="900" height="440" rx="12" fill="{background}"/>',
             f'<g font-family="Arial, sans-serif" fill="{ink}"><text x="450" y="42" text-anchor="middle" font-size="25" font-weight="700">Star History</text>',
             '<rect x="85" y="63" width="11" height="11" rx="2" fill="#e45d42"/>',
             f'<text x="106" y="74" font-size="14">{escape(project["repository"])}</text>']
    for index in range(5):
        value = ymax * index / 4
        label = f'{value:g}'
        parts.extend([f'<line x1="85" y1="{y(value):.2f}" x2="835" y2="{y(value):.2f}" stroke="{grid}"/>',
                      f'<text x="72" y="{y(value)+5:.2f}" text-anchor="end" font-size="13">{label}</text>'])
    for index in range(3):
        value = start + (end - start) * index / 2
        label = datetime.fromtimestamp(value, timezone.utc).strftime('%Y-%m-%d %H:%M')
        parts.append(f'<text x="{x(value):.2f}" y="378" text-anchor="middle" font-size="12">{label}</text>')
    path = ' '.join(('M' if i == 0 else 'L') + f'{x(at):.2f},{y(count):.2f}' for i, (at, count) in enumerate(points))
    parts.extend([f'<path d="{path}" fill="none" stroke="#e45d42" stroke-width="3" stroke-linejoin="round"/>',
                  f'<circle cx="835" cy="{y(len(stars)):.2f}" r="4" fill="#e45d42"/>',
                  f'<text x="835" y="92" text-anchor="end" font-size="14">{project["starCount"]} stars</text>',
                  '<text x="450" y="418" text-anchor="middle" font-size="13">Date (UTC)</text>',
                  '<text transform="translate(25 230) rotate(-90)" text-anchor="middle" font-size="13">GitHub Stars</text>',
                  '</g></svg>'])
    return '\n'.join(parts) + '\n'


def update(project, root=ROOT):
    if project['repository'] != REPOSITORY or not isinstance(project['starCount'], int):
        raise ValueError('Unexpected Star History source')
    images = Path(root) / 'static/images'
    images.mkdir(parents=True, exist_ok=True)
    for suffix, dark in [('light', False), ('dark', True)]:
        (images / f'star-history-{suffix}.svg').write_text(chart(project, dark), encoding='utf-8', newline='\n')
    path = Path(root) / 'data/project/star-history.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Previously fetched repository metadata')
    args = parser.parse_args()
    project = json.loads(args.input.read_text(encoding='utf-8')) if args.input else fetch_project(os.environ['GITHUB_TOKEN'])
    update(project)
    print(f'Updated Star History: {project["starCount"]} stars')
