"""Re-embed the current compiled variable font into specimen/index.html.

The specimen page carries the font inline as a base64 `data:` URI (not a
link to fonts/variable/Azrienoch-VF.ttf), so a fresh compile alone does
NOT update what the page actually shows -- this has to run afterward,
every time, or the specimen silently drifts out of sync with the real
build. Run this as the last step of any font rebuild, right after
`designspace_build.py`.
"""

from __future__ import annotations

import base64
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent.parent
FONT_PATH = HERE / "fonts" / "variable" / "Azrienoch-VF.ttf"
SPECIMEN_PATH = HERE / "specimen" / "index.html"

_SRC_RE = re.compile(r"(src:\s*url\(data:font/ttf;base64,)([^)]*)(\))")


def update_specimen() -> None:
    font_b64 = base64.b64encode(FONT_PATH.read_bytes()).decode("ascii")
    html = SPECIMEN_PATH.read_text()
    new_html, count = _SRC_RE.subn(lambda m: m.group(1) + font_b64 + m.group(3), html)
    if count != 1:
        raise RuntimeError(
            f"expected exactly one embedded-font src in {SPECIMEN_PATH}, found {count}"
        )
    SPECIMEN_PATH.write_text(new_html)
    print(f"updated {SPECIMEN_PATH} with {FONT_PATH.name} ({len(font_b64)} base64 chars)")


if __name__ == "__main__":
    update_specimen()
