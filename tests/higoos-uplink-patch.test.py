from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    page = assets / "WirelessShellPage-fixture.js"
    page.write_text(
        'const scan=O.value.encryption=se(P.encryption),anchor=n.value?(a(),N(e(oe),{key:2,modelValue:t.draft.password,'
        'const save=ce=async()=>{const P=O.value.mode,K=ae.value?.uplink;for(const _ of["2.4g","5g"])'
        'P!==_&&K?.mode===_&&await b.mutateAsync({band:_,config:{enabled:!1},apply:!0});'
        'P!=="off"&&await b.mutateAsync({band:P,config:{band:P,enabled:!0,ssid:O.value.ssid.trim(),'
        'encryption:se(O.value.encryption),password:O.value.password,hidden:!1,bssid:O.value.bssid.trim()},apply:!0})}',
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(repo / "scripts/patch-higoros-uplink-security.py"), str(root)], check=True)
    patched = page.read_text(encoding="utf-8")
    required = ('config:{band:_,enabled:!1,ssid:(K.ssid??O.value.ssid??"").trim(),',
                'encryption:K.encryption??se(O.value.encryption)',
                'hidden:K.hidden??!1,bssid:(K.bssid??O.value.bssid??"").trim()},apply:P==="off"')
    if any(value not in patched for value in required):
        raise SystemExit("ERROR: turning off an uplink does not submit the backend-required SSID and settings")
    if patched.count('config:{band:_,enabled:!1,ssid:') != 1:
        raise SystemExit("ERROR: the uplink disable payload patch is not applied exactly once")
    if 'h5000mUplinkSecurityLabel(t.draft.encryption)' not in patched:
        raise SystemExit("ERROR: uplink encryption is not shown as an automatically detected value")
    if '无法识别热点加密方式，请重新扫描后再试' not in patched:
        raise SystemExit("ERROR: unknown scan encryption would still be submitted")
    if '请填写热点密码后再保存' not in patched:
        raise SystemExit("ERROR: secured uplink can be submitted without a password")
    if 'P!==_&&K?.mode===_&&await b.mutateAsync({band:_,config:{band:_,enabled:!1,' not in patched:
        raise SystemExit("ERROR: changing uplink bands does not stage the old-band disable")
    if 'hidden:K.hidden??!1,bssid:(K.bssid??O.value.bssid??"").trim()},apply:P==="off"' not in patched:
        raise SystemExit("ERROR: the old uplink must apply immediately only when turning relay off")
    if 'onUpdate:modelValue:v=>t.draft.encryption=v' in patched:
        raise SystemExit("ERROR: uplink encryption is still manually selectable")
    if 'O.value.encryption=h5000mUplinkSecurity(P.encryption),O.value.password=""' not in patched:
        raise SystemExit("ERROR: scan selection does not set detected security and clear stale password")
print("PASS: uplink scan security is automatic and unknown encryption cannot be submitted")
print("PASS: disabling an old uplink band preserves required SSID and security fields")
