"""Local HTTP server backing `tools/corner-editor/index.html` -- a four-corner
glyph shaping tool.

Standalone by design: no dependency on ufoLib2, fontTools, or this repo's
UFO sources. Glyphs are plain JSON files under a data directory (default
`tools/corner-editor/data/`), each holding the same glyph drawn at four
variable-font extremes -- extraThin, extraBlack, condensed, wide -- as
point-compatible outlines (same contour count, same point count and order
per contour, across all four). A "regular" instance, or any point between
the extremes, is produced by bilinear interpolation of corresponding
points; see index.html for that math. This tool doesn't know anything
about Azrienoch's own axes, masters, or build pipeline -- it's meant to be
lifted into its own repo unchanged.

Run with: python3 -m tools.corner-editor.server [--port 8766]
(or, from inside tools/corner-editor/: python3 server.py [--port 8766])
Then open http://localhost:8766/ in a browser.

Endpoints:
  GET  /                       -> the editor page
  GET  /api/glyphs             -> JSON list of glyph names (data/*.json)
  GET  /api/glyph?name=<n>     -> JSON glyph {corners: {extraThin, extraBlack,
                                   condensed, wide}}, each corner
                                   {width, contours: [{points: [...]}]}
  POST /api/glyph?name=<n>     -> body = same shape -> overwrites glyph JSON
  POST /api/glyph/new?name=<n> -> creates an empty glyph (all four corners
                                   start with zero contours, width 500)
"""

from __future__ import annotations

import argparse
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
INDEX_HTML = HERE / "index.html"

CORNERS = ("extraThin", "extraBlack", "condensed", "wide")


def _empty_glyph() -> dict:
    return {
        "corners": {
            corner: {"width": 500, "contours": []} for corner in CORNERS
        }
    }


def _glyph_path(name: str) -> pathlib.Path:
    if not name or any(c in name for c in "/\\.."):
        raise ValueError("invalid glyph name")
    return DATA / f"{name}.json"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self._send_html(INDEX_HTML.read_text())
            elif parsed.path == "/api/glyphs":
                DATA.mkdir(exist_ok=True)
                names = sorted(p.stem for p in DATA.glob("*.json"))
                self._send_json({"glyphs": names})
            elif parsed.path == "/api/glyph":
                name = qs["name"][0]
                path = _glyph_path(name)
                if not path.is_file():
                    self._send_json({"error": "no such glyph"}, status=404)
                    return
                self._send_json(json.loads(path.read_text()))
            else:
                self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            name = qs["name"][0]
            path = _glyph_path(name)
            if parsed.path == "/api/glyph/new":
                DATA.mkdir(exist_ok=True)
                if path.is_file():
                    self._send_json({"error": "glyph already exists"}, status=409)
                    return
                path.write_text(json.dumps(_empty_glyph(), indent=2))
                self._send_json({"ok": True})
            elif parsed.path == "/api/glyph":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                if set(payload.get("corners", {})) != set(CORNERS):
                    self._send_json({"error": "payload must have all four corners"}, status=400)
                    return
                DATA.mkdir(exist_ok=True)
                path.write_text(json.dumps(payload, indent=2))
                self._send_json({"ok": True})
            else:
                self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"corner editor: http://localhost:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
