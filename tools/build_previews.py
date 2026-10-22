"""Render approved local PDFs into page images; never publish the PDF files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build(pdf_dir, source_catalog, renderer, root=ROOT):
    from PIL import Image
    from pypdf import PdfReader

    root, pdf_dir = Path(root), Path(pdf_dir)
    catalog = json.loads((root / 'data/textbook/catalog.json').read_text(encoding='utf-8'))
    approved = json.loads(Path(source_catalog).read_text(encoding='utf-8'))
    if approved['sourceHash'] != catalog['sourceHash']:
        raise ValueError('Preview PDFs do not match the published textbook source')
    entries = {c['id']: c for c in approved['chapters']}
    for chapter in catalog['chapters']:
        pdf = pdf_dir / (chapter['id'] + '.pdf')
        expected = entries.get(chapter['id'], {}).get('pdfSha256')
        if not expected or hashlib.sha256(pdf.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Unverified preview PDF: {chapter["id"]}')

    destination = root / 'data/textbook/previews'
    if destination.exists() and not (destination / 'index.json').is_file():
        raise ValueError('Preview output has no generation index')
    (root / '.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='page-previews-', dir=root / '.tmp') as temp:
        output = Path(temp) / 'output'
        (output / 'pages').mkdir(parents=True)

        def render(chapter):
            chapter_id = chapter['id']
            pdf = pdf_dir / (chapter_id + '.pdf')
            page_count = len(PdfReader(pdf).pages)
            folder = Path(temp) / chapter_id
            folder.mkdir()
            result = subprocess.run([str(renderer), '-scale-to-x', '1600', '-scale-to-y', '-1',
                                     '-png', str(pdf), str(folder / 'page')], capture_output=True)
            if result.returncode:
                raise ValueError(f'Could not render {chapter_id}')
            pages = []
            for path in sorted(folder.glob('page-*.png')):
                with Image.open(path) as image:
                    image = image.convert('RGB')
                    stream = BytesIO()
                    image.save(stream, format='WEBP', lossless=True, method=4)
                    data = stream.getvalue()
                    digest = hashlib.sha256(data).hexdigest()
                    filename = digest + '.webp'
                    (output / 'pages' / filename).write_bytes(data)
                    pages.append(dict(image='data/textbook/previews/pages/' + filename,
                                      width=image.width, height=image.height, sha256=digest))
            if len(pages) != page_count:
                raise ValueError(f'Incomplete page rendering for {chapter_id}')
            print(f'Rendered {chapter_id}: {len(pages)} pages', flush=True)
            return chapter_id, dict(title=chapter['title'], pageCount=page_count,
                                    pdfSha256=entries[chapter_id]['pdfSha256'], pages=pages)

        with ThreadPoolExecutor(max_workers=3) as pool:
            chapters = dict(pool.map(render, catalog['chapters']))
        index = dict(schemaVersion=1, sourceHash=catalog['sourceHash'], chapters=chapters)
        (output / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n',
                                         encoding='utf-8', newline='\n')
        if destination.exists():
            if destination.is_symlink() or destination.resolve() != root.resolve() / 'data/textbook/previews':
                raise ValueError('Unsafe preview output directory')
            shutil.rmtree(destination)
        shutil.copytree(output, destination)
    print(f'Published {sum(c["pageCount"] for c in chapters.values())} preview pages; no PDFs copied.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-dir', required=True, type=Path)
    parser.add_argument('--source-catalog', required=True, type=Path)
    parser.add_argument('--renderer', required=True, type=Path)
    args = parser.parse_args()
    build(args.pdf_dir, args.source_catalog, args.renderer)
