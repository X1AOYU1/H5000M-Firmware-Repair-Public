"""Change display branding while retaining the baseline package ABI/version."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
label = 'immortalwrt-26.10 by X1AOYU'
for name, keys in {
    'etc/openwrt_release': ['DISTRIB_DESCRIPTION'],
    'usr/lib/os-release': ['PRETTY_NAME', 'OPENWRT_RELEASE'],
}.items():
    path = root / name
    body = path.read_text(encoding='utf-8')
    for key in keys:
        body, count = re.subn(r'^' + key + r'=.*$', key + '="' + label + '"', body, flags=re.M)
        if count != 1:
            raise SystemExit('ERROR: missing branding field: ' + key)
    path.write_text(body, encoding='utf-8')
banner = root / 'etc/banner'
body = banner.read_text(encoding='utf-8')
body, count = re.subn(r'^.*ImmortalWrt 24\.10.*$', '  ' + label, body, flags=re.M)
if count != 1:
    raise SystemExit('ERROR: unexpected SSH banner')
banner.write_text(body, encoding='utf-8')
(root / 'etc/openwrt_version').write_text(label + '\n', encoding='utf-8')
print('PASS: firmware display name: ' + label + '; baseline package version retained')
