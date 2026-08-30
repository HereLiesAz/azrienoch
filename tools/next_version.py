"""Computes the release version for this build -- semantic versioning
(MAJOR.MINOR.PATCH), with a manual override that always wins over
automatic computation.

The `VERSION` file at the repo root is the single source of truth.
Normally its value is *the last released version* (whatever the release
workflow most recently tagged), and this script computes the *next* one
on top of it, automatically, from conventional-commit-style messages in
`git log` since that release's tag:

- a commit whose subject has `!` right after the type/scope (`feat!:`,
  `fix(build)!:`, ...) or whose body contains `BREAKING CHANGE` -> MAJOR
- a commit whose subject starts with `feat` (`feat:`, `feat(dots):`) ->
  MINOR
- anything else (including no matching commits at all, e.g. a
  docs/CI-only push) -> PATCH

But sometimes a bump needs to be a deliberate human decision instead --
declaring the font "finished breaking things" and moving to 1.0.0,
jumping a MAJOR version for a redesign that no single conventional-commit
message captures, or just correcting a mistake. For that, edit `VERSION`
directly and commit it: if its value isn't already an existing `vX.Y.Z`
git tag, that means a human bumped it since the last release, and this
script returns it as-is rather than computing anything on top of it.
This is also what makes the very first release work, before any tag
exists yet -- there's nothing to compute from, so whatever `VERSION`
already says is used directly.

Only decides the number. Embedding it in the built font (`ufo_build.py`)
and creating the git tag/release are separate steps.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
VERSION_FILE = HERE / "VERSION"

_SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)$")
_BREAKING_SUBJECT_RE = re.compile(r"^\w+(\([^)]*\))?!:")
_FEAT_SUBJECT_RE = re.compile(r"^feat(\([^)]*\))?:")
_MESSAGE_SEP = "\x1e===AZRIENOCH-COMMIT-END===\x1e"


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=HERE).stdout.strip()


def _parse(version: str) -> tuple[int, int, int]:
    m = _SEMVER_RE.fullmatch(version.strip())
    if not m:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _existing_tags() -> set[str]:
    out = _run(["git", "tag", "--list", "v*"])
    return set(out.splitlines()) if out else set()


def _bump_kind(messages: list[str]) -> str:
    saw_feat = False
    for msg in messages:
        subject = msg.splitlines()[0] if msg else ""
        if "BREAKING CHANGE" in msg or _BREAKING_SUBJECT_RE.match(subject):
            return "major"
        if _FEAT_SUBJECT_RE.match(subject):
            saw_feat = True
    return "minor" if saw_feat else "patch"


def next_version() -> str:
    if not VERSION_FILE.exists():
        raise SystemExit(f"{VERSION_FILE} not found -- create it with an initial version, e.g. 0.1.0")
    current = VERSION_FILE.read_text().strip()
    major, minor, patch = _parse(current)  # fail fast on a malformed VERSION file
    current_tag = f"v{current}"

    if current_tag not in _existing_tags():
        return current  # manually bumped since the last release, or the very first release

    log = _run(["git", "log", f"{current_tag}..HEAD", f"--pretty=format:%s%n%n%b{_MESSAGE_SEP}"])
    messages = [m for m in log.split(_MESSAGE_SEP) if m.strip()] if log else []
    if not messages:
        return current  # nothing new to release since the last tag

    kind = _bump_kind(messages)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


if __name__ == "__main__":
    print(next_version())
