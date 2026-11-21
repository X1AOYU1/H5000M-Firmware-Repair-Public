"""Run the packed device remark handler with the firmware's ARM64 ucode."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


root = Path(sys.argv[1]).resolve(strict=True)
module = root / "usr/share/ucode/luci/controller/higoos_device_remarks.uc"
routes = json.loads((root / "usr/share/luci/menu.d/higoos-device-remarks.json").read_text())
base = "admin/system/higoos-device-remarks"
assert routes[base]["action"]["function"] == "list"
assert routes[base + "/save"]["action"]["post"] is True
assert not any("auth" in route for route in routes.values())

with tempfile.TemporaryDirectory(prefix="h5000m-remarks-") as temp:
    store = Path(temp) / "store"
    src = module.read_text(encoding="utf-8").replace("'/etc/higoos-device-remarks'", json.dumps(str(store)))
    test = Path(temp) / "test.uc"
    test.write_text(src.replace("return {\n\tlist:", "const handlers = {\n\tlist:", 1) + r'''
function run(handler, method, user, form) {
    let code, payload;
    const env = {
        ctx: { authuser: user, authsession: 'session', authtoken: 'fixture-token' },
        http: {
            getenv: () => method,
            formvalue: (key) => form[key],
            status: (status) => { code = status; },
            header: () => {},
            prepare_content: () => {},
            write_json: (data) => { payload = data; },
        },
    };
    handlers[handler](env);
    return { code, payload };
}
const mac = '020000000001', other = '020000000002', note = '客厅手机', token = 'fixture-token';
assert(run('list', 'GET', 'guest', {}).code == 403);
assert(run('save', 'POST', 'root', { token: 'wrong', mac, note }).code == 403);
assert(run('save', 'POST', 'root', { token, mac: '../abc', note }).code == 400);
assert(run('save', 'POST', 'root', { token, mac, note }).code == 200);
assert(run('save', 'POST', 'root', { token, mac: other, note: 'PC' }).code == 200);
const readback = run('list', 'GET', 'root', {});
assert(readback.code == 200 && readback.payload.remarks[mac] == note);
assert(readback.payload.remarks[other] == 'PC');
assert(run('save', 'POST', 'root', { token, mac, note: '' }).code == 200);
assert(!run('list', 'GET', 'root', {}).payload.remarks[mac]);
assert(run('list', 'GET', 'root', {}).payload.remarks[other] == 'PC');
''', encoding="utf-8")
    subprocess.run(["qemu-aarch64-static", "-L", str(root), str(root / "usr/bin/ucode"), str(test)], check=True)

print("PASS: packed ARM64 ucode saved, read and cleared independent remarks, and denied unauthorized requests")
