"""Run the same simulation locally with Python only: python3 local_app.py."""
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import errno
import json
from pathlib import Path
from urllib.parse import urlsplit

from model import PRESETS, Settings, paired_runs, sensitivity

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type='application/json', status=200):
        if not isinstance(body, bytes):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/':
            self.send((ROOT / 'local.html').read_bytes(), 'text/html')
        elif path == '/frontend.html':
            self.send((ROOT / 'frontend.html').read_bytes(), 'text/html')
        elif path == '/api/config':
            self.send(json.dumps(dict(defaults=asdict(Settings()), presets=PRESETS)))
        elif path == '/health':
            self.send('{"status":"ok"}')
        elif path == '/favicon.ico':
            self.send(b'', 'image/x-icon', 204)
        else:
            self.send('{"error":"Not found"}', status=404)

    def do_POST(self):
        if self.path not in ('/api/simulate', '/api/compare'):
            self.send('{"error":"Not found"}', status=404)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Invalid request size')
            values = json.loads(self.rfile.read(size))
            if not isinstance(values, dict):
                raise ValueError('Settings must be an object')
            allowed = set(asdict(Settings())) - {'days', 'axons'}
            if set(values) - allowed:
                raise ValueError('Unknown settings')
            if 'scaffold' in values and type(values['scaffold']) is not bool:
                raise ValueError('scaffold must be true or false')
            for key, value in values.items():
                if key != 'scaffold' and (isinstance(value, bool) or not isinstance(value, (float, int))):
                    raise ValueError(f'{key} must be a number')
            cfg = Settings(**values)
            if self.path == '/api/compare':
                result = sensitivity(cfg)
            else:
                baseline, design = paired_runs(cfg)
                result = dict(baseline=baseline, design=design)
            self.send(json.dumps(result, separators=(',', ':'), allow_nan=False))
        except (ValueError, TypeError) as exc:
            self.send(json.dumps(dict(error=str(exc))), status=400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as exc:
        hint = 'Try --port 8502.\n' if exc.errno == errno.EADDRINUSE else 'Run python3 local_app.py from your own Terminal.\n'
        parser.exit(1, f'Could not start local preview: {exc}\n{hint}')
    print(f'Spinal Bridge Lab: http://localhost:{args.port}\nPress Control+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
