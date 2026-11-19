#!/usr/bin/env python3
"""Expose the installed OpenWrt LuCI OpenClash page from HigoOS."""
from pathlib import Path
import sys


root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
pages = sorted(assets.glob("OpenClashPage-*.js"))
controller = root / "usr/lib/lua/luci/controller/openclash.lua"
views = root / "usr/lib/lua/luci/view/openclash"
if len(pages) != 1 or not controller.is_file() or not views.is_dir():
    raise SystemExit("ERROR: the packaged native LuCI OpenClash page is missing")

path = pages[0]
source = path.read_text(encoding="utf-8")
anchor = 's("div",bl,[m(i(p),{variant:"secondary",disabled:t.value||!v.value'
link = (
    's("div",bl,[s("a",{href:"/cgi-bin/luci/admin/services/openclash",target:"_blank",'
    'rel:"noopener",class:"inline-flex items-center justify-center rounded-lg border '
    'border-line-1/70 bg-bg-1 px-3 py-2 text-sm text-txt-1 hover:bg-bg-2 focus-visible:outline-none '
    'focus-visible:ring-2 focus-visible:ring-brand"},"原生 LuCI OpenClash"),m(i(p),'
    '{variant:"secondary",disabled:t.value||!v.value'
)
if source.count(anchor) == 1:
    source = source.replace(anchor, link, 1)
elif 'href:"/cgi-bin/luci/admin/services/openclash"' not in source:
    raise SystemExit("ERROR: HigoOS OpenClash action bar changed")

path.write_text(source, encoding="utf-8")
if 'href:"/cgi-bin/luci/admin/services/openclash"' not in source or '原生 LuCI OpenClash' not in source:
    raise SystemExit("ERROR: native LuCI OpenClash link was not installed")
print("PASS: HigoOS OpenClash page links to the installed native LuCI OpenClash interface")
