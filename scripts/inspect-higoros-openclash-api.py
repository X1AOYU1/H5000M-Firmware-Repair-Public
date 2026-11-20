#!/usr/bin/env python3
"""Extract only HigoOS OpenClash API route/client snippets for build diagnostics."""
from pathlib import Path
import re
import sys


root = Path(sys.argv[1])
output = Path(sys.argv[2])
assets = root / "usr/share/higoros/web/assets"
report = []

for path in sorted(assets.glob("*.js")):
    text = path.read_text(encoding="utf-8", errors="ignore")
    needles = ("/api/v1/openclash", "openclash/file", "openclash/actions", "multipart/form-data")
    for needle in needles:
        start = 0
        while True:
            offset = text.find(needle, start)
            if offset < 0:
                break
            report.append(f"## {path.name} :: {needle} @ {offset}\n{text[max(0, offset - 700):offset + 1100]}\n")
            start = offset + len(needle)

daemon = root / "usr/bin/higorosd"
if daemon.is_file():
    data = daemon.read_bytes()
    strings = re.findall(rb"[\x20-\x7e]{6,}", data)
    selected = [item.decode("ascii", "ignore") for item in strings if any(token in item.lower() for token in (b"/api/v1/openclash", b"openclash/file", b"openclash/actions", b"multipart", b"upload"))]
    report.append("## higorosd route strings\n" + "\n".join(dict.fromkeys(selected)) + "\n")

output.write_text("\n".join(report), encoding="utf-8")
print(f"PASS: HigoOS API inspection report written ({output.stat().st_size} bytes)")
