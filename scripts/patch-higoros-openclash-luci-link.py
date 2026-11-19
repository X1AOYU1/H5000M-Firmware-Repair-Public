#!/usr/bin/env python3
"""Embed the packaged native LuCI OpenClash page inside HigoOS."""
from pathlib import Path
import sys


root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
pages = sorted(assets.glob("OpenClashPage-*.js"))
controller = root / "usr/lib/lua/luci/controller/openclash.lua"
views = root / "usr/lib/lua/luci/view/openclash"
styles = root / "www/luci-static/resources/openclash/css"
if len(pages) != 1 or not controller.is_file() or not views.is_dir():
    raise SystemExit("ERROR: the packaged native LuCI OpenClash page is missing")
if not (styles / "oc-client.css").is_file() or not (styles / "oc-common.css").is_file():
    raise SystemExit("ERROR: native LuCI OpenClash stylesheets are missing")
pages[0].write_text(
    'import{e as el,o,c as y}from"./vendor-taoyvcnH.js";'
    'const OpenClashNativeFrame=el({name:"OpenClashNativeFrame",setup(){'
    'return()=> (o(),y("iframe",{src:"/cgi-bin/luci/admin/services/openclash",'
    'title:"LuCI OpenClash",class:"w-full min-w-0 border-0 bg-white",'
    'style:"height:calc(100vh - 8rem);min-height:720px",loading:"eager",'
    'referrerpolicy:"same-origin"}))}});export{OpenClashNativeFrame as default};\n',
    encoding="utf-8",
)
source = pages[0].read_text(encoding="utf-8")
if 'y("iframe",{src:"/cgi-bin/luci/admin/services/openclash"' not in source:
    raise SystemExit("ERROR: OpenClash route does not embed native LuCI")
print("PASS: HigoOS OpenClash route embeds the native LuCI interface in a responsive iframe")
