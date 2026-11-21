#!/usr/bin/env python3
"""Inspect HigoOS persistence in an isolated network namespace with synthetic state."""
import json, os, pathlib, shutil, subprocess, sys, time, urllib.error, urllib.request, http.cookiejar
root = pathlib.Path(sys.argv[1]).resolve()
state = root / "tmp/higoros-audit-state"
runtime = root / "tmp/higoros-audit-runtime"
(root / 'tmp/sysinfo').mkdir(parents=True, exist_ok=True)
(root / 'etc/config').mkdir(parents=True, exist_ok=True)
(root / 'etc/config/network').write_text("config interface 'lan'\n	option device 'lo'\n	option proto 'static'\n	option ipaddr '127.0.0.1'\n	option netmask '255.0.0.0'\n")
(root / 'tmp/sysinfo/board_name').write_text('hiveton,h5000m\n')
state.mkdir(parents=True, exist_ok=True)
runtime.mkdir(parents=True, exist_ok=True)
shutil.copy2('/usr/bin/qemu-aarch64-static', root / 'usr/bin/qemu-aarch64-static')
(root / 'tmp/higoros-audit-state/devices-state.json').write_text('{}')
password_hash = subprocess.check_output(['openssl', 'passwd', '-6', 'synthetic-audit-only'], text=True).strip()
(root / 'etc/shadow').write_text('root:' + password_hash + ':19000:0:99999:7:::\n')
env = dict(os.environ, HIGOROS_ADDR='127.0.0.1:18080', HIGOROS_STATE_DIR='/tmp/higoros-audit-state', HIGOROS_RUNTIME_DIR='/tmp/higoros-audit-runtime', HIGOROS_FRONTEND_DIR='/usr/share/higoros/web', HIGOROS_LOG_LEVEL='debug')
subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True)
(root / 'tmp/run/ubus').mkdir(parents=True, exist_ok=True)
(root / 'dev').mkdir(exist_ok=True)
for name, minor in [('null', 3), ('urandom', 9), ('random', 8)]:
    device = root / 'dev' / name
    if not device.exists():
        os.mknod(device, 0o20666, os.makedev(1, minor))
services = []
for binary in ['/sbin/ubusd', '/sbin/rpcd']:
    services.append(subprocess.Popen(['chroot', str(root), '/usr/bin/qemu-aarch64-static', binary], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
    time.sleep(1)
print('ubusd/rpcd running:', [p.poll() is None for p in services])
for name, service in zip(['/sbin/ubusd', '/sbin/rpcd'], services):
    if service.poll() is not None:
        print('service diagnostic:', name, service.returncode, service.stderr.read().decode('utf-8', 'replace')[:2000])
daemon_log = open(root / 'tmp/higoros-audit-daemon.log', 'w+')
proc = subprocess.Popen(['chroot', str(root), '/usr/bin/qemu-aarch64-static', '/usr/sbin/higorosd'], env=env, stdout=subprocess.DEVNULL, stderr=daemon_log)
try:
    ready=False
    for _ in range(30):
        if proc.poll() is not None: break
        try:
            with urllib.request.urlopen('http://127.0.0.1:18080/', timeout=1) as r: print('HTTP root status:', r.status); ready=True; break
        except Exception: time.sleep(1)
    print('daemon running:', proc.poll() is None, 'listener ready:', ready)
    if not ready:
        daemon_log.flush(); daemon_log.seek(0); errors = daemon_log.read()
        for line in errors.splitlines():
            if any(term in line.lower() for term in ('error', 'failed', 'missing', 'not found', 'panic', 'qemu')):
                print('startup diagnostic:', line[:300])
        sys.exit(1)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    login = urllib.request.Request('http://127.0.0.1:18080/api/v1/auth/login', data=json.dumps({'username':'root','password':'synthetic-audit-only'}).encode(), headers={'Content-Type':'application/json'}, method='POST')
    try:
        with opener.open(login, timeout=30) as response: print('synthetic login:', response.status); response.read()
    except urllib.error.HTTPError as e: print('synthetic login failed:', e.code, e.read(1000).decode('utf-8', 'replace')); sys.exit(1)
    for method, path in [('GET','/api/v1/devices'), ('DELETE','/api/v1/devices/00:11:22:33:44:55')]:
        req=urllib.request.Request('http://127.0.0.1:18080'+path, method=method)
        try:
            with opener.open(req,timeout=30) as response: print(method, path, response.status, response.read(1500).decode('utf-8','replace'))
        except urllib.error.HTTPError as e: print(method, path, e.code, e.read(1500).decode('utf-8','replace'))
    time.sleep(10)
    for p in sorted(state.iterdir()):
        if p.is_file(): print('state file:', p.name, 'bytes:', p.stat().st_size)
    p=state/'devices-state.json'
    print('synthetic state JSON keys:', list(json.loads(p.read_text()).keys()))
finally:
    daemon_log.flush(); daemon_log.seek(0)
    lines = daemon_log.read().splitlines()
    failures = [line for line in lines if any(term in line.lower() for term in ('enoent', 'econnrefused', 'enodev', 'eacces', 'failed', 'error'))]
    print('daemon diagnostic failures (last 80):')
    for line in failures[-80:]: print(line[:350])
    daemon_log.close()
    for service in services: service.terminate()
    proc.terminate()
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
