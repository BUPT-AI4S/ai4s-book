import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


release = module('update_release_meta')
stars = module('update_star_history')


class ReleaseTests(unittest.TestCase):
    def test_next_release_preserves_first_launch_and_tracks_current_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'data/textbook').mkdir(parents=True)
            (root / 'data/textbook/catalog.json').write_text(json.dumps(dict(sourceCommit='latest-source')))
            first = '2026-10-22T13:51:11Z'
            release.update(first, root)
            latest = release.update(root=root)
            self.assertEqual(latest['firstPublishedAt'], first)
            self.assertEqual(latest['sourceCommit'], 'latest-source')
            self.assertEqual(latest['displayTimezone'], 'Asia/Shanghai')
            with self.assertRaisesRegex(ValueError, 'remain unchanged'):
                release.update('2026-10-23T13:51:11Z', root)

    def test_star_chart_uses_own_repository_data_in_both_themes(self):
        project = dict(repository=stars.REPOSITORY, createdAt='2026-10-22T13:00:00Z',
                       observedAt='2026-10-23T13:00:00Z', starCount=2,
                       starredAt=['2026-10-22T14:00:00Z', '2026-10-23T12:00:00Z'])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stars.update(project, root)
            for theme in ('light', 'dark'):
                tree = ET.parse(root / f'static/images/star-history-{theme}.svg')
                content = ' '.join(tree.getroot().itertext())
                self.assertIn(stars.REPOSITORY, content)
                self.assertIn('2 stars', content)
                self.assertEqual(len(tree.findall('.//{http://www.w3.org/2000/svg}path')), 1)
            saved = json.loads((root / 'data/project/star-history.json').read_text())
            self.assertEqual(saved['starredAt'], project['starredAt'])


if __name__ == '__main__':
    unittest.main()
