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
replacement = ('c(e(Ve),{modelValue:t.draft.encryption,"onUpdate:modelValue":v=>t.draft.encryption=v,'
               'options:[{value:"",label:"无法识别"},{value:"psk2",label:"WPA2"},'
               '{value:"sae-mixed",label:"WPA2/WPA3"},{value:"sae",label:"WPA3"},'
               '{value:"psk-mixed",label:"WPA/WPA2"},{value:"psk",label:"WPA"},'
               '{value:"wep-open",label:"WEP"},{value:"owe",label:"OWE"},{value:"none",label:"无加密"}],'
               'label:"热点加密方式（自动识别，可手动调整）"},null,8,["modelValue"]),') + anchor
save_old = 'const P=O.value.mode,K=ae.value?.uplink;for(const _ of["2.4g","5g"])'
save_new = ('const P=O.value.mode,K=ae.value?.uplink;'
            'if(P!=="off"&&!h5000mUplinkSecurity(O.value.encryption))throw new Error("无法识别热点加密方式，请手动选择或重新扫描");'
            'if(P!=="off"&&we(O.value.encryption)&&!O.value.password)throw new Error("请填写热点密码后再保存");'
            'for(const _ of["2.4g","5g"])')
disable_old = 'config:{enabled:!1},apply:!0'
disable_new = ('config:{band:_,enabled:!1,ssid:(K.ssid??O.value.ssid??"").trim(),'
               'encryption:K.encryption??se(O.value.encryption),'
               'password:K.password??(we(O.value.encryption)?O.value.password:""),'
               'hidden:K.hidden??!1,bssid:(K.bssid??O.value.bssid??"").trim()},'
               'apply:P==="off"')
if s.count(old) != 1 or s.count(anchor) != 1 or s.count(disable_old) != 1 or s.count(save_old) != 1:
    raise SystemExit('Wireless page anchors changed; refusing partial patch')
s = 'import{uplinkSecurity as h5000mUplinkSecurity}from"./higoos-uplink-security.js";' + s.replace(old, new, 1).replace(anchor, replacement, 1).replace(disable_old, disable_new, 1).replace(save_old, save_new, 1)
p.write_text(s, encoding='utf-8')
(assets / 'higoos-uplink-security.js').write_text((Path(__file__).parent / 'higoos-uplink-security.js').read_text(encoding='utf-8'), encoding='utf-8')
print('Patched automatic uplink security detection with manual override and complete uplink-disable payload')
