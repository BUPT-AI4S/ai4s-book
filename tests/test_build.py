import hashlib
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_textbook', ROOT / 'tools/build_textbook.py')
book = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(book)


class BookBuildTests(unittest.TestCase):
    def test_current_order_and_count(self):
        source = ROOT.parent / 'AI4SBook'
        if not source.exists():
            self.skipTest('private authoring checkout is not required in CI')
        chapters = book.read_book(source)
        self.assertEqual([c['number'] for c in chapters], [1, 2, 3])
        self.assertEqual([c['id'] for c in chapters], ['ch13-knowledge-rag', 'ch16-autonomous-laboratory', 'ch03-evaluation'])
        self.assertTrue(all(c['part'] for c in chapters))

    def test_unknown_tex_and_input_escape_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'main.tex').write_text(r'\input{../private}', encoding='utf-8')
            with self.assertRaises(ValueError):
                book.expand_inputs(source / 'main.tex', source)

    def test_snapshot_never_imports_stale_authoring_pdf(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            authoring = root / 'authoring'
            authoring.mkdir()
            (authoring / 'chapters').mkdir()
            (authoring / 'images').mkdir()
            (authoring / 'main.tex').write_text(r'\include{chapters/a}', encoding='utf-8')
            (authoring / 'chapters/a.tex').write_text(r'\chapter{新书稿}\chapterintro{目标}{基础}', encoding='utf-8')
            (authoring / 'main.pdf').write_bytes(b'%PDF-old manuscript')
            (authoring / 'images/diagram.pdf').write_bytes(b'%PDF-source figure')
            (root / '.tmp').mkdir()
            snapshot = root / '.textbook-source'
            with patch.object(book, 'ROOT', root), patch.object(book, 'SOURCE', snapshot):
                book.sync_source(authoring, snapshot)
            self.assertFalse((snapshot / 'main.pdf').exists())
            self.assertTrue((snapshot / 'images/diagram.pdf').is_file())

    def test_source_snapshot_is_private(self):
        ignore = (ROOT / '.gitignore').read_text()
        self.assertIn('.textbook-source/', ignore)
        self.assertFalse((ROOT / 'main.tex').exists())
        self.assertFalse((ROOT / 'references.bib').exists())

    def test_public_outputs(self):
        catalog = book.validate_outputs(ROOT)
        self.assertEqual(len(catalog['chapters']), 3)
        details = [json.loads((ROOT / c['contentUrl']).read_text(encoding='utf-8')) for c in catalog['chapters']]
        self.assertEqual(sum(d['html'].count('<figure') for d in details), 32)
        self.assertEqual(sum(d['html'].count('<table') for d in details), 2)
        self.assertTrue(all('??' not in d['html'] for d in details))
        for chapter in details:
            self.assertNotIn('data-reference-unresolved', chapter['html'])

    def test_generated_json_has_portable_line_endings(self):
        for path in (ROOT / 'data/textbook').rglob('*.json'):
            self.assertNotIn(b'\r\n', path.read_bytes(), path.name)

    def test_chapter_anchors_and_reference_targets_exist(self):
        class Anchors(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids, self.links = {'chapter-title'}, []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id'):
                    self.ids.add(attrs['id'])
                if tag == 'a' and attrs.get('href', '').startswith('#'):
                    self.links.append(attrs['href'][1:])
        for path in (ROOT / 'data/textbook/chapters').glob('*.json'):
            parser = Anchors()
            parser.feed(json.loads(path.read_text(encoding='utf-8'))['html'])
            self.assertTrue(set(parser.links).issubset(parser.ids), path.name)

    def test_staged_files_exclude_private_materials(self):
        staged = ROOT / '_site'
        if not staged.exists():
            self.skipTest('staging is checked separately after initial build')
        for name in ('.textbook-source', '.tmp', 'tools', 'sources', 'main.tex', 'references.bib'):
            self.assertFalse((staged / name).exists(), name)

    def test_pdf_internal_destinations_resolve(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest('optional local PDF audit; CI validates file checksums')
        for path in (ROOT / 'data/textbook/pdf').glob('*.pdf'):
            reader = PdfReader(path)
            page_ids = {p.indirect_reference.idnum for p in reader.pages}
            for name, destination in reader.named_destinations.items():
                index = reader.get_destination_page_number(destination)
                self.assertIsNotNone(index, (path.name, name))
                self.assertTrue(0 <= index < len(reader.pages), (path.name, name))
            for page in reader.pages:
                for item in page.get('/Annots', []):
                    annotation = item.get_object()
                    action = annotation.get('/A')
                    action = action.get_object() if action else {}
                    destination = annotation.get('/Dest', action.get('/D') if action.get('/S') == '/GoTo' else None)
                    if isinstance(destination, list) and destination and hasattr(destination[0], 'idnum'):
                        self.assertIn(destination[0].idnum, page_ids, path.name)


if __name__ == '__main__':
    unittest.main()
