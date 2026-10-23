import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('preview_links', ROOT / 'tools/preview_links.py')
links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(links)


class Page(dict):
    mediabox = [0, 0, 200, 400]
    def __init__(self, identity, **values):
        super().__init__(values)
        self.indirect_reference = SimpleNamespace(idnum=identity, generation=0)


class PreviewLinkTests(unittest.TestCase):
    def test_citation_resolves_exact_reference_position_and_top_left_coordinates(self):
        target = Page(20)
        source = Page(10)
        source['/Annots'] = [{'/Subtype': '/Link', '/Rect': [20, 300, 40, 320],
                             '/A': {'/S': '/GoTo', '/D': 'cite.reference'}}]
        reader = SimpleNamespace(pages=[source, target], named_destinations={
            'cite.reference': SimpleNamespace(dest_array=[target.indirect_reference, '/XYZ', 40, 240, None])})
        result = links.extract_links(reader)
        self.assertEqual(result, [[dict(page=2, x=.2, y=.4, rect=[.1, .2, .1, .05])], []])

    def test_rotated_external_link_remains_aligned_and_script_action_is_rejected(self):
        page = Page(1)
        page['/Rotate'] = 90
        page['/Annots'] = [{'/Subtype': '/Link', '/Rect': [20, 300, 40, 320],
                           '/A': {'/S': '/URI', '/URI': url}} for url in ['https://doi.org/10.1234/test', 'javascript:alert(1)']]
        result = links.extract_links(SimpleNamespace(pages=[page], named_destinations={}))
        self.assertEqual(result, [[dict(href='https://doi.org/10.1234/test', rect=[.75, .1, .05, .1])]])

    def test_unresolved_internal_link_cannot_silently_point_to_wrong_page(self):
        page = Page(1)
        page['/Annots'] = [{'/Subtype': '/Link', '/Rect': [20, 300, 40, 320],
                           '/Dest': [SimpleNamespace(idnum=999, generation=0), '/Fit']}]
        with self.assertRaisesRegex(ValueError, 'Unresolved internal'):
            links.extract_links(SimpleNamespace(pages=[page], named_destinations={}))


if __name__ == '__main__':
    unittest.main()
