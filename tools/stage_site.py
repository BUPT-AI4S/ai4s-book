"""Stage only public website files; never publish the private local snapshot."""
from pathlib import Path
import shutil
from build_textbook import validate_outputs

ROOT = Path(__file__).resolve().parents[1]

def stage(root=ROOT):
    root = Path(root).resolve()
    validate_outputs(root)
    output = root / '_site'
    if output.is_symlink() or output.resolve() != root / '_site':
        raise ValueError('Unsafe public output directory')
    if output.exists():
        if not (output / '.generated-site').is_file():
            raise ValueError('Public output lacks its generation marker')
        shutil.rmtree(output)
    output.mkdir()
    (output / '.generated-site').write_text('AI4SBook public site', encoding='utf-8')
    for filename in ('index.html', 'read.html', 'pdf.html', 'stats.html'):
        shutil.copy2(root / filename, output / filename)
    for name in ('static', 'data'):
        for path in (root / name).rglob('*'):
            if path.is_symlink():
                raise ValueError('Symlinks are not permitted in public assets')
        shutil.copytree(root / name, output / name, ignore=shutil.ignore_patterns('.*', '__pycache__', '*.pyc', '*.pdf', 'pdfjs'))
    (output / '.nojekyll').touch()
    print(f'Public website staged: {output}', flush=True)
    return output

if __name__ == '__main__':
    stage()
