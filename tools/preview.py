"""Serve the staged public website with the same /ai4s-book/ path as Pages."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / '_site'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.startswith('/ai4s-book/'):
            self.path = self.path[len('/ai4s-book'):]
        if any(part.startswith('.') for part in Path(urlsplit(self.path).path).parts):
            self.send_error(404)
            return
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8084)
    args = parser.parse_args()
    if not (ROOT / '.generated-site').is_file():
        parser.error('Run python tools/stage_site.py first')
    print(f'Book preview: http://127.0.0.1:{args.port}/ai4s-book/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
