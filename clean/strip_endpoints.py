#!/usr/bin/env python3
"""Point Kiwi-owned endpoints at 127.0.0.1 so the clean build makes no calls home.

Scans only source dirs we actually ship (not third_party/) to keep it fast.
Idempotent.
"""
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path("src").resolve()
SCAN_DIRS = ["chrome", "components", "extensions", "net", "ui", "base", "content"]
EXTS = {".java", ".xml", ".gn", ".gni", ".cc", ".h", ".py", ".json", ".js", ".grd", ".xtb", ".cpp", ".hpp"}

HOST_RE = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)*(?:kiwibrowser\.(?:com|org|io)|find\.kiwi|kiwi\.find)",
    re.IGNORECASE,
)
BARE_RE = re.compile(
    r"(?<![a-zA-Z0-9.-])(?:(?:[a-zA-Z0-9-]+\.)*(?:kiwibrowser\.(?:com|org|io)|find\.kiwi|kiwi\.find))(?![a-zA-Z0-9.-])",
    re.IGNORECASE,
)

print(f"[strip] src = {SRC}")
changed = 0
files_scanned = 0

for dirname in SCAN_DIRS:
    root = SRC / dirname
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        if ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files_scanned += 1
        new = HOST_RE.sub("http://127.0.0.1", text)
        new = BARE_RE.sub("127.0.0.1", new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(f"[strip] {path.relative_to(SRC)}")

print(f"[strip] scanned={files_scanned} changed={changed} done")
