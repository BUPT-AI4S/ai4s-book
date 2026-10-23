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
    def test_long_chapter_title_uses_required_argument(self):
        self.assertEqual(book.command_arg(r'\chapter[短标题]{完整标题}', 'chapter'), '完整标题')
        with self.assertRaisesRegex(ValueError, 'Unclosed optional'):
            book.command_arg(r'\chapter[短标题{完整标题}', 'chapter')

    def test_section_label_alias_targets_existing_section(self):
        ast = dict(blocks=[
            dict(t='Header', c=[2, ['sec:primary', [], []], [dict(t='Str', c='模型')]]),
            dict(t='RawBlock', c=['latex', r'\label{sec:alias}']),
        ])
        chapter = dict(id='model', number=3, source='chapters/model.tex')
        with patch.object(book, 'expand_inputs', return_value=''), patch.object(book, 'run', return_value=json.dumps(ast)):
            converted, references = book.parse_chapter(chapter, ROOT, 'pandoc')
        self.assertEqual(references['sec:alias'], dict(text='3.1', chapter='model', anchor='sec:primary'))
        self.assertEqual(converted['blocks'][1], dict(t='Para', c=[]))

    def test_captioned_minipage_is_one_figure_with_notes(self):
        caption = [None, [dict(t='Plain', c=[dict(t='Str', c='流程')])]]
        image = dict(t='Plain', c=[dict(t='Image', c=[['', [], []], [], ['image.png', '']])])
        inner = dict(t='Figure', c=[['fig:workflow', [], []], caption, [image]])
        note = dict(t='BlockQuote', c=[dict(t='Para', c=[dict(t='Str', c='阅读说明')])])
        ast = dict(blocks=[dict(t='Figure', c=[['fig:workflow', [], []], caption, [inner, note]])])
        with patch.object(book, 'expand_inputs', return_value=''), patch.object(book, 'run', return_value=json.dumps(ast)):
            converted, references = book.parse_chapter(dict(id='data', number=1, source='data.tex'), ROOT, 'pandoc')
        figures = [value for value in book.walk(converted) if value.get('t') == 'Figure']
        self.assertEqual(len(figures), 1)
        self.assertEqual(references['fig:workflow']['text'], '1.1')
        self.assertIn(note, figures[0]['c'][2])

    def test_current_order_and_count(self):
        source = book.SOURCE
        if not source.exists():
            self.skipTest('the pinned source snapshot is not required in CI')
        chapters = book.read_book(source)
        self.assertEqual([c['number'] for c in chapters], [1, 2, 3, 4, 5, 6])
        self.assertEqual([c['id'] for c in chapters], ['ch06-scientific-data', 'ch13-knowledge-rag', 'ch04-pretraining', 'ch05-scientific-agents', 'ch03-evaluation', 'ch16-autonomous-laboratory'])
        self.assertTrue(all(c['part'] for c in chapters))

    def test_reader_edition_removes_authoring_notes_preserving_scientific_limits(self):
        text = (r'\chapter{知识建模}' + '\n\n' +
                r'\noindent\textbf{编写说明。}原稿尚未独立核验。' + '\n\n' +
                '结论只适用于所报告的测试条件。\n' +
                r'\section*{原稿文献附注}' + '\n' +
                '原稿注明为主会论文。')
        cleaned = book.reader_tex(text)
        self.assertNotIn('编写说明', cleaned)
        self.assertNotIn('原稿', cleaned)
        self.assertIn('结论只适用于所报告的测试条件。', cleaned)
        self.assertIn(r'\chapter{知识建模}', cleaned)
        self.assertIn('文献与延伸阅读', cleaned)

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
        self.assertEqual(len(catalog['chapters']), 6)
        details = [json.loads((ROOT / c['contentUrl']).read_text(encoding='utf-8')) for c in catalog['chapters']]
        self.assertEqual(sum(d['html'].count('<figure') for d in details), 66)
        self.assertEqual(sum(d['html'].count('<table') for d in details), 12)
        self.assertEqual(catalog['statistics'], dict(chapters=6, figures=66, tables=12))
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
                self.ids, self.links, self.duplicates = {'chapter-title'}, [], []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id'):
                    if attrs['id'] in self.ids:
                        self.duplicates.append(attrs['id'])
                    self.ids.add(attrs['id'])
                if tag == 'a' and attrs.get('href', '').startswith('#'):
                    self.links.append(attrs['href'][1:])
        for path in (ROOT / 'data/textbook/chapters').glob('*.json'):
            parser = Anchors()
            parser.feed(json.loads(path.read_text(encoding='utf-8'))['html'])
            self.assertTrue(set(parser.links).issubset(parser.ids), path.name)
            self.assertEqual(parser.duplicates, [], path.name)

    def test_staged_files_exclude_private_materials(self):
        staged = ROOT / '_site'
        if not staged.exists():
            self.skipTest('staging is checked separately after initial build')
        for name in ('.textbook-source', '.tmp', 'tools', 'sources', 'main.tex', 'references.bib'):
            self.assertFalse((staged / name).exists(), name)

    def test_publication_contains_no_pdf_files_or_urls(self):
        catalog = book.validate_outputs(ROOT)
        self.assertEqual(catalog['publicationMode'], 'web-only')
        self.assertFalse(catalog.get('bookPdfUrl'))
        for chapter in catalog['chapters']:
            self.assertFalse(chapter.get('pdfUrl'))
            detail = json.loads((ROOT / chapter['contentUrl']).read_text(encoding='utf-8'))
            self.assertFalse(detail.get('pdfUrl'))
        for folder in ('data', '_site'):
            self.assertEqual(list((ROOT / folder).rglob('*.pdf')), [], folder)

    def test_pdf_publication_is_rejected(self):
        catalog = json.loads((ROOT / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
        catalog['bookPdfUrl'] = 'data/textbook/pdf/scientific-intelligence.pdf'
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'data/textbook'
            target.mkdir(parents=True)
            (target / 'catalog.json').write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'web reading only'):
                book.validate_outputs(Path(temp))

    def test_all_original_preview_pages_are_present(self):
        catalog = json.loads((ROOT / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
        index = book.validate_previews(ROOT, catalog)
        self.assertEqual([index['chapters'][c['id']]['pageCount'] for c in catalog['chapters']], [66, 48, 42, 30, 38, 33])

    def test_original_preview_preserves_citation_link_destinations(self):
        index = json.loads((ROOT / 'data/textbook/previews/index.json').read_text(encoding='utf-8'))
        chapter = index['chapters']['ch06-scientific-data']
        links = chapter['pages'][1].get('links', [])
        self.assertGreater(len(links), 0, 'Page 2 citations must remain clickable')
        self.assertEqual(links[1]['page'], 52)
        self.assertTrue(all(0 <= value <= 1 for value in links[1]['rect']))

    def test_preview_version_mismatch_is_rejected(self):
        catalog = json.loads((ROOT / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
        catalog['sourceHash'] = 'unmatched-edition'
        with self.assertRaisesRegex(ValueError, 'Preview source version mismatch'):
            book.validate_previews(ROOT, catalog)


if __name__ == '__main__':
    unittest.main()
