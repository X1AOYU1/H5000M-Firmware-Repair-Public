#!/usr/bin/env python3
"""Make station security explicit and keep scan-derived passwords usable."""
from pathlib import Path
import sys

assets = Path(sys.argv[1]) / 'usr/share/higoros/web/assets'
files = list(assets.glob('WirelessShellPage-*.js'))
if len(files) != 1:
    raise SystemExit(f'Expected one wireless page, found {len(files)}')
p = files[0]
s = p.read_text(encoding='utf-8')
old = 'O.value.encryption=se(P.encryption)'
new = 'O.value.encryption=h5000mUplinkSecurity(P.encryption),O.value.password=""'
anchor = 'n.value?(a(),N(e(oe),{key:2,modelValue:t.draft.password'
replacement = 'c(e(Ve),{modelValue:t.draft.encryption,"onUpdate:modelValue":v=>t.draft.encryption=v,options:[{value:"psk2",label:"WPA2"},{value:"sae-mixed",label:"WPA2/WPA3"},{value:"sae",label:"WPA3"},{value:"psk-mixed",label:"WPA/WPA2"},{value:"psk",label:"WPA"},{value:"wep-open",label:"WEP"},{value:"owe",label:"OWE"},{value:"none",label:"无密码"}],label:"热点加密方式（请核对）"},null,8,["modelValue"]),' + anchor
if s.count(old) != 1 or s.count(anchor) != 1:
    raise SystemExit('Wireless page anchors changed; refusing partial patch')
s = 'import{uplinkSecurity as h5000mUplinkSecurity}from"./higoos-uplink-security.js";' + s.replace(old, new, 1).replace(anchor, replacement, 1)
p.write_text(s, encoding='utf-8')
(assets / 'higoos-uplink-security.js').write_text((Path(__file__).parent / 'higoos-uplink-security.js').read_text(encoding='utf-8'), encoding='utf-8')
print('Patched wireless station scan security and selector')
