"""Publish an explicit snapshot of AI4SBook as chapter HTML/MathML and LaTeX PDFs."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.textbook-source'
REPO = 'https://github.com/BUPT-AI4S/AI4SBook'
PDF_PUBLICATION_ENABLED = False
PREAMBLE = r'''
\newcommand{\chapterintro}[2]{\textbf{学习目标：}#1\par\textbf{先修知识：}#2。\par}
\newcommand{\chapterplan}[2]{\chapterintro{#1}{#2}}
\newcommand{\chaptersummary}[1]{\section*{本章小结}#1}
\newcommand{\labheading}[1]{\subsubsection*{#1}}
\newcommand{\keyterm}[1]{\emph{#1}}
\newcommand{\vect}[1]{\boldsymbol{#1}}
\newcommand{\R}{\mathbb{R}}
\newcommand{\E}{\mathbb{E}}
\newcommand{\argmin}{\operatorname*{arg\,min}}
'''


def uncomment(text):
    return '\n'.join(re.split(r'(?<!\\)%', line, maxsplit=1)[0] for line in text.split('\n'))


def inside(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Path outside textbook source: {path.name}')
    return path


def expand_inputs(path, root, stack=()):
    path = inside(path, root)
    if path in stack:
        raise ValueError(f'LaTeX input cycle: {path.name}')
    text = uncomment(path.read_text(encoding='utf-8'))
    def expand(match):
        target = Path(match[1])
        if not target.suffix:
            target = target.with_suffix('.tex')
        return expand_inputs(Path(root) / target, root, (*stack, path))
    return re.sub(r'\\(?:input|include)\s*\{([^{}]+)\}', expand, text)


def argument(text, start):
    """Read one balanced TeX group, preserving nested formatting and escaped braces."""
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != '{':
        raise ValueError('Expected a braced LaTeX argument')
    depth, end = 1, start + 1
    while end < len(text):
        if text[end] == '\\':
            end += 2
            continue
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:end], end + 1
        end += 1
    raise ValueError('Unclosed LaTeX argument')


def command_arg(text, name):
    match = re.search(r'\\' + name + r'\b\s*', text)
    if not match:
        return ''
    position = match.end()
    if text[position:position + 1] == '[':
        depth, position = 1, position + 1
        while position < len(text) and depth:
            if text[position] == '\\':
                position += 2
                continue
            depth += (text[position] == '[') - (text[position] == ']')
            position += 1
        if depth:
            raise ValueError('Unclosed optional LaTeX argument')
    return argument(text, position)[0]


def read_book(source):
    source = Path(source)
    main = uncomment((source / 'main.tex').read_text(encoding='utf-8'))
    chapters, part, part_number = [], '教材内容', 1
    for match in re.finditer(r'\\(part|include)\s*\{([^{}]+)\}', main):
        if match[1] == 'part':
            part, part_number = match[2], part_number + 1
        elif match[2].startswith('chapters/'):
            filename = match[2] + '.tex'
            path = inside(source / filename, source)
            text = expand_inputs(path, source)
            title = re.sub(r'\\\\\s*', '', command_arg(text, 'chapter'))
            if not title:
                raise ValueError(f'Missing chapter title: {filename}')
            slug = path.stem
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', slug):
                raise ValueError(f'Unsafe chapter slug: {slug}')
            summary = command_arg(text, 'chapter(?:intro|plan)')
            summary = re.sub(r'\\[a-zA-Z]+|[{}]', '', summary)
            if not summary:
                summary = {
                    'ch06-scientific-data': '理解科学数据的分类、资源、质量与治理，建立从科学问题到 AI-ready 数据与研究反馈的完整路径。',
                    'ch13-knowledge-rag': '理解科学知识的组织、表示与建模，以及检索、推理和科研任务中知识的使用方法。',
                    'ch16-autonomous-laboratory': '理解计算决策、实验执行和测量反馈如何形成闭环，并比较不同领域自主实验室的实现。',
                }.get(slug, title)
            chapters.append(dict(id=slug, number=len(chapters) + 1, title=title,
                                 part=part, partNumber=part_number, source=filename,
                                 status='available',
                                 hasCitations=bool(re.search(r'\\cite\w*\b', text)),
                                 summary=summary))
    if not chapters or len({c['id'] for c in chapters}) != len(chapters):
        raise ValueError('Missing or duplicate textbook chapters')
    return chapters


def reader_tex(text):
    """Omit authoring logistics from the reading edition; retain scientific content."""
    text = re.sub(r'(?m)^\\noindent\\textbf\{编写说明。\}[^\n]*(?:\n|$)', '', text)
    text = text.replace(r'\textbf{当前版本为协作编写稿，只收录已经提供完整原稿的章节。}', '')
    text = re.sub(r'(?m)^三章均保留原稿[^\n]*',
                  '各章结合研究案例、图表与学习目标展开讨论，参考文献统一列于书末，便于读者延伸阅读。', text)
    text = text.replace(r'\chapter*{阅读与编写指南}', r'\chapter*{阅读指南}')
    text = text.replace(r'\section*{当前内容与阅读顺序}', r'\section*{内容与阅读顺序}')
    text = text.split(r'\section*{协作编写约定}', 1)[0]
    text = text.replace('原稿文献附注', '文献与延伸阅读')
    text = text.replace('原稿摘要', '摘要')
    text = re.sub(r'\\begin\{minipage\}\{\\linewidth\}\\footnotesize\\linespread\{1\.15\}\\selectfont 原稿第[^\n]*?\\end\{minipage\}', '', text)
    text = text.replace('以下保留原稿的发表背景说明及补充项目入口', '以下补充文献的发表背景说明与项目入口')
    text = text.replace('以下保留原稿文献表中的说明，完整条目统一列于书末；出版背景按原稿转录。',
                        '以下介绍代表性文献的研究主题与发表信息，完整条目统一列于书末。')
    text = text.replace('原稿第三节“本节主参考综述”', '科学智能测评的参考综述')
    text = text.replace('原稿访问日期', '访问日期')
    text = text.replace('原稿注明', '文献信息注明')
    text = text.replace('这一视角也明确了本章与第一章的分工' +
                        r'\footnote{编者注：此处“第一章”为原稿内部编排指称，所述科学数据一般质量的内容目前尚未作为独立章节收录；并非指当前书稿的第1章。}' +
                        '：第一章讨论科学数据作为研究资源的一般质量，包括准确性、完整性、组织方式和可复用性；本章讨论这些数据作为能力测量工具是否合适。',
                        '这一视角也明确了科学数据质量与测评数据适用性的区别：科学数据作为研究资源的一般质量包括准确性、完整性、组织方式和可复用性；本章讨论这些数据作为能力测量工具是否合适。')
    text = text.replace(r'\newcommand{\BookEdition}{协作编写稿}', r'\newcommand{\BookEdition}{2026年10月版}')
    text = text.replace(r'\newcommand{\BookEnglishTitle}{SCIENTIFIC INTELLIGENCE', r'\newcommand{\BookEnglishTitle}{AI FOR SCIENCE')
    return text


def prepare_tex(text):
    text = reader_tex(uncomment(text))
    # Preserve semantic tips while discarding only their TeX box configuration.
    def tip(match):
        position = match.end()
        label, position = argument(text, position)
        if match[1] == 'figuretip':
            title, position = argument(text, position)
            heading = r'小贴士（图~\ref{' + label + '}：' + title + '）'
        else:
            heading = '小贴士（' + label + '）'
        return match.start(), position, r'\begin{quote}\textbf{' + heading + r'}\par '
    replacements = [tip(m) for m in re.finditer(r'\\begin\{(figuretip|booktip)\}(?:\[[^\]]*\])?', text)]
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    text = re.sub(r'\\end\{(?:figuretip|booktip)\}', r'\\end{quote}', text)
    text = re.sub(r'\\begin\{minipage\}\{\\linewidth\}(\s*\\captionsetup\{type=(table|figure)\}[\s\S]*?)\\end\{minipage\}', lambda m: '\\begin{' + m[2] + '}' + m[1] + '\\end{' + m[2] + '}', text)
    # The source uses captionof inside center/minipage instead of floating figures.
    text = re.sub(r'\\begin\{center\}\s*\\begin\{minipage\}(?:\[[^\]]*\])?\{\\linewidth\}', r'\\begin{figure}', text)
    text = re.sub(r'\\end\{minipage\}\s*\\end\{center\}', r'\\end{figure}', text)
    text = text.replace(r'\captionof{figure}', r'\caption')
    text = text.replace(r'\begin{exercises}', r'\section*{思考与练习}\begin{enumerate}')
    text = text.replace(r'\end{exercises}', r'\end{enumerate}')
    text = re.sub(r'\\begin\{minipage\}\{\\linewidth\}|\\end\{minipage\}', ' ', text)
    text = re.sub(r'\\(?:fontsize)\{[^{}]*\}\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\(?:linespread|addvspace|markright)\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\renewcommand\{\\arraystretch\}\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\addlinespace(?:\[[^\]]*\])?', ' ', text)
    text = re.sub(r'\\allowbreak(?![A-Za-z])\s*', '', text)
    # Presentation-only commands have no semantic content in a flowing webpage.
    text = re.sub(r'\\(?:captionsetup|color)\s*\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\setlength\s*\{[^{}]*\}\s*\{[^{}]*\}', ' ', text)
    text = re.sub(r'\\hsize\s*=\s*[0-9.]+\\hsize|\\linewidth\s*=\s*\\hsize', '', text)
    text = re.sub(r'\\(?:normalfont|clearpage|cleardoublepage|centering|raggedright|arraybackslash|footnotesize|small|selectfont|noindent|begingroup|endgroup)(?![A-Za-z])', ' ', text)
    return PREAMBLE + '\n' + text


def source_hash(source):
    digest = hashlib.sha256()
    for path in sorted(Path(source).rglob('*')):
        if path.is_file() and path.name != 'provenance.json':
            digest.update(path.relative_to(source).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def sync_source(authoring, target=SOURCE):
    authoring, target = Path(authoring).resolve(), Path(target).resolve()
    if authoring == target or target != SOURCE.resolve():
        raise ValueError('Unsafe textbook snapshot destination')
    read_book(authoring)
    if target.exists() and not (target / 'provenance.json').is_file():
        raise ValueError('Snapshot directory has no provenance marker')
    with tempfile.TemporaryDirectory(prefix='textbook-source-', dir=ROOT / '.tmp') as tmp:
        snapshot = Path(tmp)
        for path in authoring.rglob('*'):
            rel = path.relative_to(authoring)
            if any(p.startswith('.') for p in rel.parts) or rel.parts[0] in {'sources', 'examples'}:
                continue
            if path.is_symlink():
                raise ValueError('Symlinks are not allowed in textbook source')
            # Only image PDFs are source assets. Authoring main.pdf and other
            # compiled output must never bypass a fresh manuscript compilation.
            if path.suffix.lower() == '.pdf' and rel.parts[0] != 'images':
                continue
            if path.is_file() and path.suffix.lower() in {'.tex', '.sty', '.bst', '.bib', '.png', '.jpg', '.jpeg', '.svg', '.pdf'}:
                output = snapshot / rel
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, output)
        result = subprocess.run(['git', '-c', f'safe.directory={authoring.as_posix()}', '-C', str(authoring), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        status = subprocess.run(['git', '-c', f'safe.directory={authoring.as_posix()}', '-C', str(authoring), 'status', '--porcelain'], capture_output=True, text=True)
        provenance = dict(repository=REPO, commit=result.stdout.strip() if result.returncode == 0 else None,
                          workingTreeModified=bool(status.stdout.strip()), sourceHash=source_hash(snapshot))
        (snapshot / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(snapshot, target)
    print(f'Synchronized textbook snapshot: {provenance["sourceHash"][:12]}', flush=True)


def run(command, cwd, input=None, env=None):
    result = subprocess.run([str(x) for x in command], cwd=cwd, input=input, text=True,
                            encoding='utf-8', errors='replace', capture_output=True, env=env)
    if result.returncode:
        raise ValueError(f'{Path(command[0]).name} failed:\n{result.stdout[-3500:]}\n{result.stderr[-3500:]}')
    return result.stdout


def find_pandoc():
    if executable := shutil.which('pandoc'):
        return executable
    try:
        import pypandoc
        return pypandoc.get_pandoc_path()
    except ImportError:
        raise ValueError('Pandoc is required. Install tools/textbook-requirements.txt or pandoc.') from None


def walk(value):
    if isinstance(value, dict):
        yield value
        # Cite's fallback is deliberately raw TeX; citeproc resolves it below.
        if value.get('t') == 'Cite':
            return
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class Contents(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items, self.current = [], None

    def handle_starttag(self, tag, attrs):
        if tag in {'h2', 'h3', 'h4'}:
            self.current = dict(level=int(tag[1]), id=dict(attrs).get('id', ''), title='')

    def handle_data(self, data):
        if self.current is not None:
            self.current['title'] += data

    def handle_endtag(self, tag):
        if self.current is not None and tag in {'h2', 'h3', 'h4'}:
            if self.current['id']:
                self.items.append(self.current)
            self.current = None


def parse_chapter(chapter, source, pandoc):
    text = prepare_tex(expand_inputs(source / chapter['source'], source))
    ast = json.loads(run([pandoc, '--from=latex+latex_macros+raw_tex', '--to=json', '--fail-if-warnings'], source, text))
    # Pandoc can duplicate a captioned minipage inside its surrounding figure.
    # Keep one semantic figure while preserving its image and reading notes.
    for element in walk(ast):
        if element.get('t') == 'Figure':
            identity, caption, blocks = element['c']
            flattened = []
            for child in blocks:
                if child.get('t') == 'Figure' and child['c'][0][0] == identity[0] and child['c'][1] == caption:
                    flattened.extend(child['c'][2])
                else:
                    flattened.append(child)
            blocks[:] = flattened
    section_numbers, figure_number, table_number = [chapter['number'], 0, 0, 0, 0, 0], 0, 0
    references, last_reference = {}, None
    for element in walk(ast):
        kind, content = element.get('t'), element.get('c')
        alias = re.fullmatch(r'\\label\{([^{}]+)\}', content[1].strip()) if kind in {'RawBlock', 'RawInline'} and content[0] in {'latex', 'tex'} else None
        if alias and last_reference:
            references[alias[1]] = dict(last_reference)
            element['t'], element['c'] = ('Para', []) if kind == 'RawBlock' else ('Str', '')
            continue
        if kind == 'Div' and content[0][0]:
            for child in content[1]:
                if child.get('t') == 'Table':
                    child['c'][0][0], content[0][0] = content[0][0], ''
                    break
        if kind in {'RawBlock', 'RawInline'} and content[0] in {'latex', 'tex'} and content[1].strip() and not re.fullmatch(r'\\ref\*?\{[^{}]+\}', content[1].strip()):
            raise ValueError(f'{chapter["id"]}: unsupported LaTeX; add a web mapping: {content[1][:160]}')
        if kind == 'Header' and content[0] > 1 and 'unnumbered' not in content[1][1]:
            level = content[0] - 1
            section_numbers[level] += 1
            section_numbers[level + 1:] = [0] * (len(section_numbers) - level - 1)
            prefix = '.'.join(str(n) for n in section_numbers[:level + 1])
            content[2][:0] = [{'t': 'Str', 'c': prefix}, {'t': 'Space'}]
            if content[1][0]:
                references[content[1][0]] = dict(text=prefix, chapter=chapter['id'])
        if kind == 'Header' and content[0] == 1 and content[1][0]:
            references[content[1][0]] = dict(text=str(chapter['number']), chapter=chapter['id'], anchor='chapter-title')
        if kind == 'Figure':
            figure_number += 1
            caption = content[1][1]
            if caption and caption[0]['t'] in {'Plain', 'Para'}:
                caption[0]['c'][:0] = [{'t': 'Str', 'c': f'图 {chapter["number"]}.{figure_number}'}, {'t': 'Space'}]
            if content[0][0]:
                references[content[0][0]] = dict(text=f'{chapter["number"]}.{figure_number}', chapter=chapter['id'])
        if kind == 'Table':
            table_number += 1
            caption = content[1][1]
            if caption and caption[0]['t'] in {'Plain', 'Para'}:
                caption[0]['c'][:0] = [{'t': 'Str', 'c': f'表 {chapter["number"]}.{table_number}'}, {'t': 'Space'}]
            if content[0][0]:
                references[content[0][0]] = dict(text=f'{chapter["number"]}.{table_number}', chapter=chapter['id'])
        identity = content[1][0] if kind == 'Header' else content[0][0] if kind in {'Figure', 'Table'} else None
        if identity in references:
            last_reference = dict(references[identity], anchor=references[identity].get('anchor', identity))
    return ast, references


def convert_chapter(chapter, source, output, pandoc, ast=None, references=None):
    ast, local = parse_chapter(chapter, source, pandoc) if ast is None else (ast, {})
    references = references or local
    for element in walk(ast):
        kind, content = element.get('t'), element.get('c')
        if kind in {'RawInline', 'RawBlock'} and content[0] in {'latex', 'tex'}:
            match = re.fullmatch(r'\\ref\*?\{([^{}]+)\}', content[1].strip())
            if match:
                target = references.get(match[1])
                if not target:
                    raise ValueError(f'Unresolved textbook reference: {match[1]}')
                anchor = target.get('anchor', match[1])
                url = '#' + anchor if target['chapter'] == chapter['id'] else 'read.html?chapter=' + target['chapter'] + '#' + anchor
                element['t'], element['c'] = 'Link', [['', [], []], [{'t': 'Str', 'c': target['text']}], [url, '']]
        if kind == 'Image':
            original = content[2][0]
            image = inside(source / original, source)
            if not image.is_file():
                image = inside(source / 'images' / original, source)
            if not image.is_file():
                raise ValueError(f'Missing textbook image: {original}')
            rel = image.relative_to(source)
            asset = output / 'assets' / rel
            asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, asset)
            content[2][0] = 'data/textbook/assets/' + rel.as_posix()
    # Drop chapter heading only; the page supplies its own accessible h1.
    ast['blocks'] = [block for block in ast['blocks'] if not (block.get('t') == 'Header' and block['c'][0] == 1)]
    html = run([pandoc, '--from=json', '--to=html5', '--mathml', '--citeproc',
                '--bibliography', source / 'references.bib', '--csl', ROOT / 'tools/textbook-numeric.csl',
                '--metadata=reference-section-title:参考文献', '--metadata=link-citations:true',
                '--metadata=lang:en-US', '--fail-if-warnings'], source, json.dumps(ast))
    # citeproc inserts an h1 for its bibliography; the reader owns the sole h1.
    html = re.sub(r'<h1\b', '<h2', html).replace('</h1>', '</h2>')
    toc = Contents()
    toc.feed(html)
    return dict(html=html, toc=toc.items)


def compile_and_split(source, work, output, chapters, engine, reuse_verified_pdf=False):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    if reuse_verified_pdf and (work / 'main.pdf').is_file():
        pass
    elif 'tectonic' in Path(engine).name:
        run([engine, '--keep-logs', 'main.tex'], work, env=dict(os.environ, TECTONIC_UNTRUSTED_MODE='1'))
    else:
        run([engine, '-xelatex', '-interaction=nonstopmode', '-halt-on-error', '-no-shell-escape', 'main.tex'], work)
    pdf = work / 'main.pdf'
    reader = PdfReader(pdf)
    def flatten(items):
        for item in items:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield str(item.title), reader.get_destination_page_number(item)
    bookmarks = list(flatten(reader.outline))
    starts = []
    for chapter in chapters:
        candidates = [page for title, page in bookmarks if chapter['title'] in re.sub(r'\s+', '', title)]
        if len(candidates) != 1:
            raise ValueError(f'Cannot locate unique PDF chapter bookmark: {chapter["title"]}')
        starts.append(candidates[0])
    ref_pages = [page for title, page in bookmarks if '参考文献' in title]
    if not ref_pages or starts != sorted(set(starts)):
        raise ValueError('Missing reference section or invalid PDF chapter order')
    refs = ref_pages[-1]
    shutil.copy2(pdf, output / 'pdf/scientific-intelligence.pdf')
    for index, chapter in enumerate(chapters):
        end = starts[index + 1] if index + 1 < len(starts) else refs
        writer = PdfWriter()
        chapter_reader = PdfReader(pdf)
        # Resolve named GoTo links before cloning pages, preserving exact fit/XYZ
        # positions and avoiding the writer's ambiguous named-link pairing.
        for page in chapter_reader.pages:
            for item in page.get('/Annots', []):
                annotation = item.get_object()
                action = annotation.get('/A')
                container = action.get_object() if action and action.get_object().get('/S') == '/GoTo' else annotation
                key = '/D' if container is not annotation else '/Dest'
                name = container.get(key)
                if isinstance(name, str) and name in chapter_reader.named_destinations:
                    container[NameObject(key)] = chapter_reader.named_destinations[name].dest_array
        writer.append(chapter_reader, pages=list(range(starts[index], end)) + list(range(refs, len(reader.pages))))
        writer.add_metadata({'/Title': chapter['title'], '/Author': '鄂海红 徐坤', '/Subject': '科学智能原理与实践'})
        path = output / 'pdf' / (chapter['id'] + '.pdf')
        with path.open('wb') as stream:
            writer.write(stream)
        chapter['pages'] = len(writer.pages)
    return len(reader.pages)








def build_book(source=SOURCE, root=ROOT, pdf_engine=None, html_only=False, preview_pdf_engine=None):
    if not PDF_PUBLICATION_ENABLED:
        html_only = True
    source, root = Path(source).resolve(), Path(root).resolve()
    chapters = read_book(source)
    fingerprint = source_hash(source)
    provenance = json.loads((source / 'provenance.json').read_text(encoding='utf-8'))
    if fingerprint != provenance['sourceHash']:
        raise ValueError('Textbook snapshot changed; synchronize from the authoring repository again.')
    # Include rendering code/style in cache identity, not just the manuscript.
    build_hash = hashlib.sha256((fingerprint + Path(__file__).read_text(encoding='utf-8') +
                                (ROOT / 'tools/textbook-numeric.csl').read_text(encoding='utf-8')).encode()).hexdigest()
    destination = root / 'data/textbook'
    previous = {}
    if (destination / 'catalog.json').is_file():
        previous = json.loads((destination / 'catalog.json').read_text(encoding='utf-8'))
    if destination.exists() and not (destination / '.generated-textbook').is_file():
        raise ValueError('Textbook output has no generation marker')
    engine = pdf_engine or shutil.which('latexmk') or shutil.which('tectonic')
    if not html_only and not engine:
        raise ValueError('PDF compilation requires latexmk + XeLaTeX, or --pdf-engine /path/to/tectonic.')
    pandoc = find_pandoc()
    (root / '.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='textbook-publish-', dir=root / '.tmp') as temp:
        output = Path(temp) / 'output'
        for name in ('chapters', 'pdf'):
            (output / name).mkdir(parents=True, exist_ok=True)
        if previous.get('sourceHash') == fingerprint and (destination / 'previews/index.json').is_file():
            validate_previews(root, previous)
            shutil.copytree(destination / 'previews', output / 'previews')
        cover = source / 'images/cover/scientific-unity-v1.png'
        if cover.is_file():
            (output / 'assets/images/cover').mkdir(parents=True, exist_ok=True)
            shutil.copy2(cover, output / 'assets/images/cover' / cover.name)
        work = Path(temp) / 'latex'
        shutil.copytree(source, work)
        # Apply the same reader-facing text to HTML and the compiled PDF copy.
        # The pinned authoring snapshot remains unchanged for reproducibility.
        for path in work.rglob('*'):
            if path.suffix in {'.tex', '.bib'}:
                path.write_text(reader_tex(path.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
        documents, references = {}, {}
        for chapter in chapters:
            ast, local = parse_chapter(chapter, source, pandoc)
            documents[chapter['id']] = ast
            overlap = references.keys() & local.keys()
            if overlap:
                raise ValueError(f'Duplicate textbook labels: {sorted(overlap)}')
            references.update(local)
        converted_chapters = {chapter['id']: convert_chapter(chapter, source, output, pandoc, documents[chapter['id']], references) for chapter in chapters}
        full_pdf = output / 'pdf/scientific-intelligence.pdf'
        cached = PDF_PUBLICATION_ENABLED and html_only and previous.get('sourceHash') == fingerprint and previous.get('pdfVersion') == 4 and bool(previous.get('bookPdfUrl'))
        total_pages = previous.get('pages', 0) if previous.get('sourceHash') == fingerprint else 0
        if preview_pdf_engine:
            private = Path(temp) / 'preview-sources'
            (private / 'pdf').mkdir(parents=True)
            print('Compiling local preview sources; PDF files remain outside public output', flush=True)
            total_pages = compile_and_split(source, work, private, chapters, preview_pdf_engine)
            private_catalog = dict(sourceHash=fingerprint, sourceCommit=provenance.get('commit'),
                                   chapters=[dict(chapter, pdfSha256=hashlib.sha256((private / 'pdf' / (chapter['id'] + '.pdf')).read_bytes()).hexdigest()) for chapter in chapters])
            (private / 'catalog.json').write_text(json.dumps(private_catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            archive = root / '.tmp/preview-sources'
            if archive.is_symlink() or archive.resolve() != root / '.tmp/preview-sources':
                raise ValueError('Unsafe local preview source directory')
            if archive.exists():
                if not (archive / 'catalog.json').is_file():
                    raise ValueError('Local preview sources lack their catalog')
                shutil.rmtree(archive)
            shutil.copytree(private, archive)
        if not html_only:
            print('Compiling complete manuscript and splitting chapter PDFs', flush=True)
            previous_pdf = destination / 'pdf/scientific-intelligence.pdf'
            reuse_verified_pdf = False
            if previous.get('sourceHash') == fingerprint and previous.get('buildHash') == build_hash and previous.get('pdfVersion') == 4 and previous_pdf.is_file() and hashlib.sha256(previous_pdf.read_bytes()).hexdigest() == previous.get('bookPdfSha256'):
                shutil.copy2(previous_pdf, work / 'main.pdf')
                reuse_verified_pdf = True
            total_pages = compile_and_split(source, work, output, chapters, engine, reuse_verified_pdf)
        elif cached:
            validate_outputs(root)
            for pdf in (destination / 'pdf').glob('*.pdf'):
                shutil.copy2(pdf, output / 'pdf' / pdf.name)
            total_pages = previous.get('pages', 0)
        for chapter in chapters:
            converted = converted_chapters[chapter['id']]
            pdf = destination / 'pdf' / (chapter['id'] + '.pdf')
            chapter['pdfUrl'] = 'data/textbook/pdf/' + pdf.name if (cached or not html_only) else None
            chapter['pdfSha256'] = hashlib.sha256((output / 'pdf' / pdf.name).read_bytes()).hexdigest() if chapter['pdfUrl'] else None
            chapter['contentUrl'] = 'data/textbook/chapters/' + chapter['id'] + '.json'
            detail = dict(chapter, **converted, sourceHash=fingerprint)
            (output / 'chapters' / (chapter['id'] + '.json')).write_text(json.dumps(detail, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
            chapter['contentSha256'] = hashlib.sha256((output / 'chapters' / (chapter['id'] + '.json')).read_bytes()).hexdigest()
        info = (source / 'book-info.tex').read_text(encoding='utf-8')
        title_match = re.search(r'\\newcommand\{\\BookTitle\}', info)
        title = argument(info, title_match.end())[0] if title_match else '科学智能原理与实践'
        statistics = dict(chapters=len(chapters), figures=sum(value['html'].count('<figure') for value in converted_chapters.values()),
                          tables=sum(value['html'].count('<table') for value in converted_chapters.values()))
        catalog = dict(schemaVersion=1, publicationMode='web-only', pdfVersion=4, title=title, sourceHash=fingerprint, buildHash=build_hash, statistics=statistics,
                       sourceRepository=provenance['repository'], sourceCommit=provenance.get('commit'),
                       pages=total_pages, bookPdfUrl='data/textbook/pdf/scientific-intelligence.pdf' if full_pdf.is_file() else None,
                       bookPdfSha256=hashlib.sha256(full_pdf.read_bytes()).hexdigest() if full_pdf.is_file() else None, chapters=chapters)
        (output / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        (output / '.generated-textbook').write_text('AI4S generated textbook', encoding='utf-8')
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(output, destination)
    print(f'Built {len(chapters)} textbook chapters; source {fingerprint[:12]}', flush=True)
    return catalog


def validate_previews(root, catalog):
    root = Path(root).resolve()
    folder = root / 'data/textbook/previews'
    index = json.loads((folder / 'index.json').read_text(encoding='utf-8'))
    if index.get('schemaVersion') != 1 or index.get('sourceHash') != catalog['sourceHash']:
        raise ValueError('Preview source version mismatch; rebuild the page previews')
    if index.get('linkVersion') != 1:
        raise ValueError('Preview link annotations are missing')
    if set(index.get('chapters', {})) != {chapter['id'] for chapter in catalog['chapters']}:
        raise ValueError('Preview chapter list does not match the textbook')
    verified = set()
    for chapter in catalog['chapters']:
        preview = index['chapters'][chapter['id']]
        pages = preview.get('pages', [])
        if not pages or preview.get('pageCount') != len(pages) or preview.get('title') != chapter['title']:
            raise ValueError('Incomplete textbook preview')
        for page in pages:
            if not isinstance(page.get('links'), list):
                raise ValueError('Preview link annotations are missing')
            for link in page['links']:
                rect = link.get('rect', [])
                if len(rect) != 4 or any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in rect) or rect[2] <= 0 or rect[3] <= 0 or rect[0] + rect[2] > 1.000001 or rect[1] + rect[3] > 1.000001:
                    raise ValueError('Invalid preview link rectangle')
                if 'page' in link:
                    if not isinstance(link['page'], int) or not 1 <= link['page'] <= len(pages) or any(not isinstance(link.get(key), (int, float)) or not 0 <= link[key] <= 1 for key in ('x', 'y')):
                        raise ValueError('Invalid preview page link')
                elif not isinstance(link.get('href'), str) or not re.match(r'^(https?://|mailto:)', link['href'], re.I):
                    raise ValueError('Invalid preview external link')
            path = page.get('image', '')
            if not re.fullmatch(r'data/textbook/previews/pages/[a-f0-9]{64}\.webp', path):
                raise ValueError('Invalid preview page path')
            if page.get('width') != 1600 or not isinstance(page.get('height'), int) or page['height'] <= 0:
                raise ValueError('Invalid preview page dimensions')
            asset = inside(root / path, folder)
            if asset.name != page.get('sha256', '') + '.webp':
                raise ValueError('Invalid preview page checksum')
            if path not in verified:
                data = asset.read_bytes()
                if data[:4] != b'RIFF' or data[8:12] != b'WEBP' or hashlib.sha256(data).hexdigest() != page['sha256']:
                    raise ValueError('Preview page checksum mismatch')
                verified.add(path)
    if {path.relative_to(root).as_posix() for path in (folder / 'pages').glob('*')} != verified:
        raise ValueError('Unlisted preview page assets')
    return index


def validate_outputs(root=ROOT, require_pdfs=False):
    """Validate committed public outputs without access to the private manuscript."""
    root = Path(root).resolve()
    catalog = json.loads((root / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
    chapters = catalog['chapters']
    if not PDF_PUBLICATION_ENABLED:
        if catalog.get('publicationMode') != 'web-only' or catalog.get('bookPdfUrl') or any(c.get('pdfUrl') for c in chapters):
            raise ValueError('The public edition supports web reading only')
        if any((root / 'data/textbook').rglob('*.pdf')):
            raise ValueError('PDF files must not be included in the public edition')
    if catalog.get('schemaVersion') != 1 or not chapters or len({c['id'] for c in chapters}) != len(chapters):
        raise ValueError('Invalid textbook catalog')
    if require_pdfs or catalog.get('bookPdfUrl'):
        if catalog.get('bookPdfUrl') != 'data/textbook/pdf/scientific-intelligence.pdf':
            raise ValueError('Missing complete book PDF')
        full = (root / catalog['bookPdfUrl']).read_bytes()
        if not full.startswith(b'%PDF-') or hashlib.sha256(full).hexdigest() != catalog['bookPdfSha256']:
            raise ValueError('Invalid complete book PDF')
    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'img':
                path = inside(root / dict(attrs)['src'], root / 'data/textbook/assets')
                if not path.is_file():
                    raise ValueError('Missing published textbook image')
    for number, chapter in enumerate(chapters, 1):
        if chapter['number'] != number or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', chapter['id']):
            raise ValueError('Invalid textbook chapter identity/order')
        expected_content = 'data/textbook/chapters/' + chapter['id'] + '.json'
        if chapter['contentUrl'] != expected_content:
            raise ValueError('Invalid chapter content URL')
        content_path = root / expected_content
        detail = json.loads(content_path.read_text(encoding='utf-8'))
        if not PDF_PUBLICATION_ENABLED and detail.get('pdfUrl'):
            raise ValueError('Chapter data must not expose a PDF URL')
        if detail['sourceHash'] != catalog['sourceHash'] or detail['id'] != chapter['id']:
            raise ValueError('Mixed textbook source versions')
        if hashlib.sha256(content_path.read_bytes()).hexdigest() != chapter['contentSha256']:
            raise ValueError('Chapter content checksum mismatch; rebuild the textbook')
        Images().feed(detail['html'])
        if require_pdfs or chapter.get('pdfUrl'):
            expected_pdf = 'data/textbook/pdf/' + chapter['id'] + '.pdf'
            if chapter.get('pdfUrl') != expected_pdf or detail.get('pdfUrl') != expected_pdf:
                raise ValueError(f'Missing PDF for {chapter["id"]}; run a full textbook build')
            data = (root / expected_pdf).read_bytes()
            if not data.startswith(b'%PDF-') or hashlib.sha256(data).hexdigest() != chapter['pdfSha256']:
                raise ValueError('Invalid or stale chapter PDF; rebuild the textbook')
    validate_previews(root, catalog)
    print(f'Validated {len(chapters)} published chapters, previews and their assets', flush=True)
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync-from', type=Path, help='Explicitly refresh source snapshot from local AI4SBook')
    parser.add_argument('--pdf-engine', help='Path to latexmk or tectonic')
    parser.add_argument('--preview-pdf-engine', help='Compile local PDF sources for page previews without publishing PDF files')
    parser.add_argument('--html-only', action='store_true', help='Preview HTML; do not advertise missing/stale PDFs')
    parser.add_argument('--check', action='store_true', help='Validate published outputs without private source or a LaTeX engine')
    args = parser.parse_args()
    try:
        (ROOT / '.tmp').mkdir(exist_ok=True)
        if args.check:
            validate_outputs()
        else:
            if args.sync_from:
                sync_source(args.sync_from)
            build_book(pdf_engine=args.pdf_engine, html_only=args.html_only, preview_pdf_engine=args.preview_pdf_engine)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Textbook build failed: {error}\n')
