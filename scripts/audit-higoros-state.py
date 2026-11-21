#!/usr/bin/env python3
"""Inspect HigoOS persistence in an isolated network namespace with synthetic state."""
import json, os, pathlib, shutil, subprocess, sys, time, urllib.error, urllib.request
root = pathlib.Path(sys.argv[1]).resolve()
state = root / "tmp/higoros-audit-state"
runtime = root / "tmp/higoros-audit-runtime"
state.mkdir(parents=True, exist_ok=True)
runtime.mkdir(parents=True, exist_ok=True)
shutil.copy2('/usr/bin/qemu-aarch64-static', root / 'usr/bin/qemu-aarch64-static')
(root / 'tmp/higoros-audit-state/devices-state.json').write_text('{}')
env = dict(os.environ, HIGOROS_ADDR='127.0.0.1:18080', HIGOROS_STATE_DIR='/tmp/higoros-audit-state', HIGOROS_RUNTIME_DIR='/tmp/higoros-audit-runtime', HIGOROS_FRONTEND_DIR='/usr/share/higoros/web', HIGOROS_LOG_LEVEL='error')
subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
proc = subprocess.Popen(['chroot', str(root), '/usr/bin/qemu-aarch64-static', '/usr/sbin/higorosd'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    ready=False
    for _ in range(30):
        if proc.poll() is not None: break
        try:
            with urllib.request.urlopen('http://127.0.0.1:18080/', timeout=1) as r: print('HTTP root status:', r.status); ready=True; break
        except Exception: time.sleep(1)
    print('daemon running:', proc.poll() is None, 'listener ready:', ready)
    if not ready: sys.exit(1)
    for method in ['GET','DELETE']:
        req=urllib.request.Request('http://127.0.0.1:18080/api/devices/00:11:22:33:44:55', method=method)
        try:
            with urllib.request.urlopen(req,timeout=3) as r: print(method,'synthetic device status:',r.status)
        except urllib.error.HTTPError as e: print(method,'synthetic device status:',e.code)
    time.sleep(10)
    for p in sorted(state.iterdir()):
        if p.is_file(): print('state file:', p.name, 'bytes:', p.stat().st_size)
    p=state/'devices-state.json'
    print('synthetic state JSON keys:', list(json.loads(p.read_text()).keys()))
finally:
    proc.terminate()
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
