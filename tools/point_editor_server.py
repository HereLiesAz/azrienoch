"""Local HTTP server backing `tools/point_editor.html` -- a drag-the-points
glyph editor that reads and writes the actual UFO master sources directly
(not a copy, not a JSON export/import round trip), so an edit made in the
browser is immediately the real source of truth for that glyph/master.

Run with: python3 -m tools.point_editor_server [--port 8765]
Then open http://localhost:8765/ in a browser.

Endpoints:
  GET  /                          -> the editor page itself
  GET  /api/masters                -> JSON list of UFO master directory names
  GET  /api/glyphs?master=<ufo>    -> JSON list of glyph names in that master
  GET  /api/glyph?master=..&name=..-> JSON {width, contours: [{points: [...]}]}
  POST /api/glyph?master=..&name=..body=same shape -> overwrites that glyph's
       contours in that master's UFO and saves it to disk immediately.

This intentionally only ever touches ONE glyph, in ONE master, at a time --
it is a hand-editing/demonstration tool for working out what a shape SHOULD
be, not a replacement for the generative quirks.py pipeline. A rebuild
(`python3 -m tools.designspace_build`) still regenerates every master from
Roboto Flex + the quirks pipeline from scratch, which will overwrite any
hand edit made here unless it's also encoded as a real rule in quirks.py
(or the target glyph is excluded from whatever quirk would otherwise
overwrite it). Treat this tool's output as a reference/spec, not a
permanent edit, unless told otherwise.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import ufoLib2
from ufoLib2.objects import Contour, Point

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES = HERE / "sources"
EDITOR_HTML = pathlib.Path(__file__).resolve().parent / "point_editor.html"

_font_cache: dict[str, ufoLib2.Font] = {}


def _load_font(master: str) -> ufoLib2.Font:
    if master not in _font_cache:
        path = SOURCES / master
        if not path.is_dir():
            raise FileNotFoundError(master)
        _font_cache[master] = ufoLib2.Font.open(path)
    return _font_cache[master]


def _glyph_to_json(glyph) -> dict:
    return {
        "name": glyph.name,
        "width": glyph.width,
        "contours": [
            {
                "points": [
                    {
                        "x": p.x,
                        "y": p.y,
                        "type": p.type,
                        "smooth": bool(p.smooth),
                    }
                    for p in contour.points
                ]
            }
            for contour in glyph.contours
        ],
    }


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
        pass  # keep stdout quiet -- errors still raise

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self._send_html(EDITOR_HTML.read_text())
            elif parsed.path == "/api/masters":
                masters = sorted(p.name for p in SOURCES.iterdir() if p.suffix == ".ufo")
                self._send_json({"masters": masters})
            elif parsed.path == "/api/glyphs":
                master = qs["master"][0]
                font = _load_font(master)
                names = sorted(font.layers.defaultLayer.keys())
                self._send_json({"glyphs": names})
            elif parsed.path == "/api/glyph":
                master = qs["master"][0]
                name = qs["name"][0]
                font = _load_font(master)
                glyph = font[name]
                self._send_json(_glyph_to_json(glyph))
            else:
                self._send_json({"error": "not found"}, status=404)
        except Exception as exc:  # surfaced to the browser, not swallowed
            self._send_json({"error": str(exc)}, status=500)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path != "/api/glyph":
                self._send_json({"error": "not found"}, status=404)
                return
            master = qs["master"][0]
            name = qs["name"][0]
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))

            font = _load_font(master)
            glyph = font[name]
            glyph.clearContours()
            for contour_spec in payload["contours"]:
                points = [
                    Point(
                        x=p["x"],
                        y=p["y"],
                        type=p["type"],
                        smooth=bool(p.get("smooth", False)),
                    )
                    for p in contour_spec["points"]
                ]
                glyph.contours.append(Contour(points=points))
            font.save(SOURCES / master, overwrite=True)
            self._send_json({"ok": True})
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"point editor: http://localhost:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
