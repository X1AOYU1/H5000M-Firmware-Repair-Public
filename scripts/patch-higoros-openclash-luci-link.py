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
app_pages = sorted(assets.glob("LuciAppPage-*.js"))
if len(pages) != 1 or not controller.is_file() or not views.is_dir():
    raise SystemExit("ERROR: the packaged native LuCI OpenClash page is missing")
if not (styles / "oc-client.css").is_file() or not (styles / "oc-common.css").is_file():
    raise SystemExit("ERROR: native LuCI OpenClash stylesheets are missing")
if len(app_pages) != 1:
    raise SystemExit("ERROR: HigoOS LuCI app launcher bundle is missing")

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

app_path = app_pages[0]
app_source = app_path.read_text(encoding="utf-8")
is_openclash = 'a.value?.luciUrl?.toLowerCase().includes("/services/openclash")'
openclash_url = f'{is_openclash}?"/apps/openclash":x(a.value)'
resolver_anchor = 's=l(()=>x(a.value))'
resolver_replacement = f's=l(()=>{openclash_url})'
if app_source.count(resolver_anchor) == 1:
    app_source = app_source.replace(resolver_anchor, resolver_replacement, 1)
elif resolver_replacement not in app_source:
    raise SystemExit("ERROR: HigoOS LuCI app link resolver changed")

link_anchor = 'href:s.value,target:"_blank",rel:"noopener"'
link_replacement = f'href:s.value,target:{is_openclash}?"_self":"_blank",rel:"noopener"'
if app_source.count(link_anchor) == 1:
    app_source = app_source.replace(link_anchor, link_replacement, 1)
elif link_replacement not in app_source:
    raise SystemExit("ERROR: HigoOS LuCI app link target changed")
app_path.write_text(app_source, encoding="utf-8")
if openclash_url not in app_source or link_replacement not in app_source:
    raise SystemExit("ERROR: OpenClash app center shortcut does not open the embedded HigoOS route")
print("PASS: OpenClash app center button opens the HigoOS embedded OpenClash route")
