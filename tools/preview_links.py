"""Convert PDF link annotations to normalized, image-aligned preview links."""
import math
from urllib.parse import urlsplit


def obj(value):
    return value.get_object() if hasattr(value, 'get_object') else value


def point(page, x, y):
    left, bottom, right, top = map(float, page.mediabox)
    u, v = (x - left) / (right - left), (top - y) / (top - bottom)
    angle = int(page.get('/Rotate', 0)) % 360
    u, v = {0: (u, v), 90: (1 - v, u), 180: (1 - u, 1 - v), 270: (v, 1 - u)}[angle]
    return tuple(round(max(0, min(1, value)), 8) for value in (u, v))


def safe_url(value):
    if not isinstance(value, str) or any(ord(char) < 32 for char in value):
        return False
    parsed = urlsplit(value)
    return (parsed.scheme in {'http', 'https'} and bool(parsed.netloc)) or (parsed.scheme == 'mailto' and bool(parsed.path))


def extract_links(reader):
    refs = {(page.indirect_reference.idnum, page.indirect_reference.generation): index
            for index, page in enumerate(reader.pages) if page.indirect_reference}
    names = reader.named_destinations
    result = []
    for page in reader.pages:
        links = []
        for annotation in page.get('/Annots', []):
            annotation = obj(annotation)
            if annotation.get('/Subtype') != '/Link' or len(annotation.get('/Rect', [])) != 4:
                continue
            action = obj(annotation.get('/A', {}))
            link = {}
            if action.get('/S') == '/URI':
                href = action.get('/URI')
                if not safe_url(href):
                    continue
                link['href'] = str(href)
            else:
                destination = action.get('/D') if action.get('/S') == '/GoTo' else annotation.get('/Dest')
                if isinstance(destination, str):
                    destination = names[destination].dest_array if destination in names else None
                destination = obj(destination)
                if not isinstance(destination, (list, tuple)) or len(destination) < 2:
                    continue
                reference = destination[0]
                target = refs.get((reference.idnum, reference.generation)) if hasattr(reference, 'idnum') else reference if isinstance(reference, int) else None
                if target is None or not 0 <= target < len(reader.pages):
                    raise ValueError('Unresolved internal preview link')
                target_page = reader.pages[target]
                x, y = float(target_page.mediabox[0]), float(target_page.mediabox[3])
                def number(index, default):
                    try:
                        value = float(destination[index])
                        return value if math.isfinite(value) else default
                    except (IndexError, TypeError, ValueError):
                        return default
                kind = destination[1]
                if kind == '/XYZ':
                    x, y = number(2, x), number(3, y)
                elif kind in {'/FitH', '/FitBH'}:
                    y = number(2, y)
                elif kind in {'/FitV', '/FitBV'}:
                    x = number(2, x)
                elif kind == '/FitR':
                    x, y = number(2, x), number(5, y)
                link.update(page=target + 1, x=point(target_page, x, y)[0], y=point(target_page, x, y)[1])
            x0, y0, x1, y1 = map(float, annotation['/Rect'])
            corners = [point(page, x, y) for x in (x0, x1) for y in (y0, y1)]
            left, top = min(p[0] for p in corners), min(p[1] for p in corners)
            width, height = max(p[0] for p in corners) - left, max(p[1] for p in corners) - top
            if width > 0 and height > 0:
                link['rect'] = [left, top, round(width, 8), round(height, 8)]
                links.append(link)
        result.append(links)
    return result
