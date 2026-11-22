#!/usr/bin/env python3
"""Check mobile PWA assets and firmware installation wiring."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
source = repo / "scripts/higoos-mobile"
app = (source / "app.js").read_text(encoding="utf-8")
worker = (source / "sw.js").read_text(encoding="utf-8")
manifest = (source / "manifest.webmanifest").read_text(encoding="utf-8")
for marker in ("/auth/me", "/auth/login", "/devices", "/system/info", "/system/resources",
               "/system/realtime-speed", "/wifi/settings", "/system/reboot", "credentials: 'same-origin'"):
    if marker not in app:
        raise SystemExit(f"ERROR: mobile app is missing {marker}")
if "localStorage.setItem" in app or "localStorage.getItem" in app:
    raise SystemExit("ERROR: mobile app must not store router credentials or session tokens")
if "url.pathname.startsWith('/api/')" not in worker:
    raise SystemExit("ERROR: service worker does not exclude API responses from caching")
if '"start_url": "/mobile/"' not in manifest or '"display": "standalone"' not in manifest:
    raise SystemExit("ERROR: mobile web app manifest is not installable")
subprocess.run(["node", "--check", str(source / "app.js")], check=True)
subprocess.run(["node", "--check", str(source / "sw.js")], check=True)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "usr/share/higoros/web").mkdir(parents=True)
    subprocess.run([sys.executable, str(repo / "scripts/patch-higoros-mobile-app.py"), str(root)], check=True)
    installed = root / "usr/share/higoros/web/mobile"
    if {path.name for path in installed.iterdir()} != {path.name for path in source.iterdir()}:
        raise SystemExit("ERROR: firmware mobile PWA install is incomplete")
build = (repo / "scripts/build-public-node-free-wallpaper.sh").read_text(encoding="utf-8")
if 'patch-higoros-mobile-app.py "$OUT/rootfs"' not in build:
    raise SystemExit("ERROR: firmware build does not install the mobile PWA")
print("PASS: HigoOS mobile PWA uses same-origin auth, is installable, and is included in firmware")
