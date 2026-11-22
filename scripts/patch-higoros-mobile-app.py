#!/usr/bin/env python3
"""Install the standalone HigoOS mobile PWA into the firmware web root."""
from pathlib import Path
import shutil
import sys


def install(root: Path) -> None:
    source = Path(__file__).resolve().parent / "higoos-mobile"
    target = root / "usr/share/higoros/web/mobile"
    required = {"index.html", "app.css", "app.js", "manifest.webmanifest", "sw.js", "icon.svg"}
    missing = sorted(name for name in required if not (source / name).is_file())
    if missing:
        raise SystemExit(f"ERROR: mobile PWA assets missing: {', '.join(missing)}")
    target.mkdir(parents=True, exist_ok=True)
    for name in required:
        shutil.copyfile(source / name, target / name)
    print(f"PASS: installed HigoOS mobile PWA at {target.relative_to(root)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-mobile-app.py ROOTFS_DIR")
    install(Path(sys.argv[1]))
