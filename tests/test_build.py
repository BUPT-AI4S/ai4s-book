import hashlib
import importlib.util
import json
import shutil
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
    def test_pdf_split_uses_chapter_bookmarks_when_section_repeats_short_title(self):
        from pypdf import PdfWriter, PdfReader
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            output = work / 'output'
            (output / 'pdf').mkdir(parents=True)
            writer = PdfWriter()
            for _ in range(3):
                writer.add_blank_page(width=200, height=300)
            parent = writer.add_outline_item('第二章 科学知识建模', 0)
            writer.add_outline_item('2.1 科学知识建模研究', 0, parent=parent)
            writer.add_outline_item('第三章 科学模型', 1)
            writer.add_outline_item('参考文献', 2)
            with (work / 'main.pdf').open('wb') as stream:
                writer.write(stream)
            chapters = [dict(id='knowledge', title='科学知识建模'), dict(id='models', title='科学模型')]
            self.assertEqual(book.compile_and_split(work, work, output, chapters, 'unused', True), 3)
            self.assertEqual(len(PdfReader(output / 'pdf/knowledge.pdf').pages), 2)

    @unittest.skipUnless(shutil.which('pandoc') or importlib.util.find_spec('pypandoc'), 'Pandoc is required')
    def test_continued_figure_retains_its_number_and_next_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'chapter.tex').write_text(r'\chapter{知识}\begin{figure}\includegraphics{a.png}\caption{上半}\label{fig:timeline}\end{figure}\begin{figure}\ContinuedFloat\includegraphics{b.png}\caption{下半}\end{figure}\begin{figure}\includegraphics{c.png}\caption{下一张}\label{fig:next}\end{figure}', encoding='utf-8')
            ast, refs = book.parse_chapter(dict(id='knowledge', number=2, source='chapter.tex'), source, book.find_pandoc())
            figures = [node for node in book.walk(ast) if node.get('t') == 'Figure']
            self.assertEqual(len(figures), 3)
            self.assertEqual(refs['fig:timeline']['text'], '2.1')
            self.assertEqual(refs['fig:next']['text'], '2.2')
            self.assertIn('continued-figure', figures[1]['c'][0][1])

    @unittest.skipUnless(shutil.which('pandoc') or importlib.util.find_spec('pypandoc'), 'Pandoc is required')
    def test_rendered_tikz_keeps_figure_caption_number_and_reference(self):
        diagram = r'\begin{tikzpicture}\node{知识分类};\end{tikzpicture}'
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'chapter.tex').write_text(r'\chapter{知识}\begin{figure}' + diagram + r'\caption{知识分类图}\label{fig:taxonomy}\end{figure}见图\ref{fig:taxonomy}。', encoding='utf-8')
            ast, refs = book.parse_chapter(dict(id='knowledge', number=2, source='chapter.tex'), source,
                                          book.find_pandoc(), {diagram: 'images/web-tikz/diagram.pdf'})
            figures = [node for node in book.walk(ast) if node.get('t') == 'Figure']
            images = [node for node in book.walk(ast) if node.get('t') == 'Image']
            self.assertEqual(len(figures), 1)
            self.assertEqual(len(images), 1)
            self.assertEqual(images[0]['c'][2][0], 'images/web-tikz/diagram.pdf')
            self.assertEqual(refs['fig:taxonomy']['text'], '2.1')
            self.assertIn('知识分类图', json.dumps(ast, ensure_ascii=False))

    def test_legacy_section_links_survive_source_renumbering_without_duplicate_ids(self):
        html='<h2 id="sec:ch01-2">分类</h2><figure id="fig:ch01-1"></figure>'
        chapter=dict(id='ch06-scientific-data',source='chapters/ch01-scientific-data.tex')
        aliased=book.legacy_anchor_aliases(html,chapter)
        self.assertIn('id="sec:ch06-2"',aliased)
        self.assertIn('id="fig:ch06-1"',aliased)
        self.assertEqual(book.legacy_anchor_aliases(aliased,chapter),aliased)

    @unittest.skipUnless(shutil.which('pandoc') or importlib.util.find_spec('pypandoc'), 'Pandoc is required to regenerate chapter ASTs')
    def test_multiline_table_cells_do_not_become_extra_numbered_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)
            (source/'chapter.tex').write_text(r'\chapter{Table}\begin{table}\caption{Roles}\label{tab:roles}\begin{tabular}{cc}Role & Task \\\begin{tabular}[c]{@{}c@{}}First\\Second\end{tabular} & Analysis \\\end{tabular}\end{table}\begin{table}\caption{Next}\label{tab:next}\begin{tabular}{cc}A & B\\\end{tabular}\end{table}',encoding='utf-8')
            ast,refs=book.parse_chapter(dict(id='sample',number=1,source='chapter.tex'),source,book.find_pandoc())
            self.assertEqual(len([x for x in book.walk(ast) if x.get('t')=='Table']),2)
            self.assertEqual(refs['tab:next']['text'],'1.2')
            self.assertIn('First',json.dumps(ast));self.assertIn('Second',json.dumps(ast))

    def test_chapter_renumbering_aligns_legacy_table_labels_and_new_references(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp);(source/'chapters').mkdir()
            (source/'chapters/ch01-scientific-data.tex').write_text(r'\chapter{数据}\label{tab:ch06-1}见\ref{tab:ch01-1}。',encoding='utf-8')
            text=book.chapter_tex(dict(id='ch06-scientific-data',source='chapters/ch01-scientific-data.tex'),source)
            self.assertIn(r'\label{tab:ch01-1}',text)
            self.assertIn(r'\ref{tab:ch01-1}',text)

    def test_duplicate_print_labels_are_scoped_to_their_chapter(self):
        text=r'\chapter{模型}\label{chap:model}\label{tab:shared}见表\ref{tab:shared}和图\ref{fig:unique}。'
        actual=book.scope_duplicate_labels(text,'models',{'tab:shared'})
        self.assertIn(r'\label{models:tab:shared}',actual)
        self.assertIn(r'\ref{models:tab:shared}',actual)
        self.assertIn(r'\ref{fig:unique}',actual)
        self.assertIn(r'\label{chap:model}',actual)

    def test_scaled_wide_table_retains_caption_citations_and_cells(self):
        text=r'\begin{table*}[t]\caption{评价\cite{source}}\resizebox{\textwidth}{!}{\begin{tabular}{cc}模型 & $x_{i}$ \\\end{tabular}}\end{table*}'
        converted=book.prepare_tex(text)
        self.assertNotIn(r'\resizebox',converted)
        self.assertIn(r'\begin{table}',converted)
        self.assertIn(r'\caption{评价\cite{source}}',converted)
        self.assertIn(r'模型 & $x_{i}$',converted)
        self.assertIn(r'\end{tabular}\end{table}',converted)

    @unittest.skipUnless(shutil.which('pdftoppm') and importlib.util.find_spec('PIL') and importlib.util.find_spec('pypdf'), 'Figure generation requires Poppler, Pillow and pypdf')
    def test_pdf_figure_is_published_as_an_image_without_exposing_source_pdf(self):
        from pypdf import PdfWriter
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';output=root/'output'
            (source/'images').mkdir(parents=True);output.mkdir()
            pdf=source/'images/diagram.pdf';writer=PdfWriter();writer.add_blank_page(width=200,height=100)
            with pdf.open('wb') as stream:writer.write(stream)
            url=book.publish_image(pdf,source,output)
            self.assertEqual(url,'data/textbook/assets/images/diagram.webp')
            with Image.open(output/'assets/images/diagram.webp') as image:
                self.assertEqual(image.width,2200)
                self.assertEqual(image.height,1100)
            self.assertEqual(list(output.rglob('*.pdf')),[])

    def test_renamed_authoring_files_keep_published_reader_links(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp);(source/'chapters').mkdir()
            names=['ch01-scientific-data','ch02-knowledge-rag','ch03-pretraining','ch04-scientific-agents','ch05-evaluation','ch06-autonomous-laboratory']
            (source/'main.tex').write_text('\n'.join(r'\include{chapters/'+name+'}' for name in names),encoding='utf-8')
            for name in names:(source/'chapters'/f'{name}.tex').write_text(r'\chapter{'+name+'}',encoding='utf-8')
            chapters=book.read_book(source)
            self.assertEqual([c['id'] for c in chapters],['ch06-scientific-data','ch13-knowledge-rag','ch04-pretraining','ch05-scientific-agents','ch03-evaluation','ch16-autonomous-laboratory'])
            self.assertEqual(chapters[0]['source'],'chapters/ch01-scientific-data.tex')

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
            (authoring / 'fonts').mkdir()
            (authoring / 'fonts/rare.otf').write_bytes(b'author-supplied font')
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
            self.assertEqual((snapshot/'fonts/rare.otf').read_bytes(),b'author-supplied font')

    def test_source_snapshot_is_private(self):
        ignore = (ROOT / '.gitignore').read_text()
        self.assertIn('.textbook-source/', ignore)
        self.assertFalse((ROOT / 'main.tex').exists())
        self.assertFalse((ROOT / 'references.bib').exists())

    def test_public_outputs(self):
        catalog = book.validate_outputs(ROOT)
        self.assertEqual(len(catalog['chapters']), 6)
        details = [json.loads((ROOT / c['contentUrl']).read_text(encoding='utf-8')) for c in catalog['chapters']]
        self.assertEqual(sum(d['html'].count('<figure') for d in details), 60)
        self.assertEqual(sum(d['html'].count('<table') for d in details), 13)
        self.assertEqual(catalog['statistics'], dict(chapters=6, figures=60, tables=13))
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
        self.assertEqual([index['chapters'][c['id']]['pageCount'] for c in catalog['chapters']], [69, 61, 45, 33, 40, 35])

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
