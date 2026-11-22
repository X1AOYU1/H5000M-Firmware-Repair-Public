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
    if '"onUpdate:modelValue":v=>t.draft.encryption=v' not in patched:
        raise SystemExit("ERROR: uplink security manual override is missing")
    if '热点加密方式（自动识别，可手动调整）' not in patched:
        raise SystemExit("ERROR: automatic detection and manual override are not explained")
    if '{value:"sae-mixed",label:"WPA2/WPA3"}' not in patched or '{value:"psk2",label:"WPA2"}' not in patched:
        raise SystemExit("ERROR: common WPA2 and WPA3 security modes cannot be selected manually")
    if '无法识别热点加密方式，请手动选择或重新扫描' not in patched:
        raise SystemExit("ERROR: unknown scan encryption would still be submitted")
    if '请填写热点密码后再保存' not in patched:
        raise SystemExit("ERROR: secured uplink can be submitted without a password")
    if 'P!==_&&K?.mode===_&&await b.mutateAsync({band:_,config:{band:_,enabled:!1,' not in patched:
        raise SystemExit("ERROR: changing uplink bands does not stage the old-band disable")
    if 'hidden:K.hidden??!1,bssid:(K.bssid??O.value.bssid??"").trim()},apply:P==="off"' not in patched:
        raise SystemExit("ERROR: the old uplink must apply immediately only when turning relay off")
    if 'O.value.encryption=h5000mUplinkSecurity(P.encryption),O.value.password=""' not in patched:
        raise SystemExit("ERROR: scan selection does not set detected security and clear stale password")
print("PASS: uplink scan security is automatic and unknown encryption cannot be submitted")
print("PASS: disabling an old uplink band preserves required SSID and security fields")
