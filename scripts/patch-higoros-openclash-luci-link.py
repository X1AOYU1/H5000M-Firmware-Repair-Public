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
launcher = assets / "higoos-openclash-launcher.js"
launcher_source = (
    '(()=>{if(window.__higoosOpenClashLauncher)return;'
    'window.__higoosOpenClashLauncher=true;'
    'document.addEventListener("click",e=>{'
    'const t=e.target instanceof Element?e.target:null;'
    'const c=t&&t.closest("a,button");if(!c)return;'
    'let matched=(c.getAttribute("href")||"").toLowerCase().includes("openclash");'
    'if(!matched){let n=c;for(let i=0;n&&i<5;i++,n=n.parentElement){'
    'const s=(n.innerText||n.textContent||"").toLowerCase();'
    'if(s.includes("openclash")&&s.includes("打开")){matched=true;break}}}'
    'if(!matched)return;e.preventDefault();e.stopImmediatePropagation();'
    'if(document.getElementById("higoos-openclash-frame"))return;'
    'const o=document.createElement("div");o.id="higoos-openclash-frame";'
    'Object.assign(o.style,{position:"fixed",inset:"0",zIndex:"2147483000",'
    'background:"#f3f5f8",display:"flex",flexDirection:"column"});'
    'const b=document.createElement("div");Object.assign(b.style,{height:"48px",flex:"0 0 48px",'
    'display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 16px",'
    'background:"#fff",borderBottom:"1px solid #d9dee8",font:"14px sans-serif"});'
    'const h=document.createElement("strong");h.textContent="OpenClash";'
    'const x=document.createElement("button");x.type="button";x.textContent="关闭";'
    'Object.assign(x.style,{padding:"6px 12px",cursor:"pointer"});'
    'x.addEventListener("click",()=>o.remove());b.append(h,x);'
    'const f=document.createElement("iframe");f.title="LuCI OpenClash";'
    'f.src="/cgi-bin/luci/admin/services/openclash";'
    'Object.assign(f.style,{width:"100%",height:"calc(100% - 48px)",flex:"1",border:"0",background:"#fff"});'
    'o.append(b,f);document.body.append(o)},true)})();\n'
)
existing = launcher.read_text(encoding="utf-8") if launcher.exists() else None
if existing not in (None, launcher_source):
    raise SystemExit("ERROR: unexpected HigoOS OpenClash launcher asset")
launcher.write_text(launcher_source, encoding="utf-8")

index = root / "usr/share/higoros/web/index.html"
if not index.is_file():
    raise SystemExit("ERROR: HigoOS web entry index.html is missing")
html = index.read_text(encoding="utf-8")
script_tag = '<script defer src="./assets/higoos-openclash-launcher.js"></script>'
if script_tag not in html:
    if html.count("</body>") != 1:
        raise SystemExit("ERROR: HigoOS index body marker is missing or ambiguous")
    html = html.replace("</body>", script_tag + "</body>", 1)
    index.write_text(html, encoding="utf-8")
if script_tag not in html or 'f.src="/cgi-bin/luci/admin/services/openclash"' not in launcher_source:
    raise SystemExit("ERROR: global OpenClash click launcher was not installed")
print("PASS: global HigoOS click handler opens native LuCI in an in-shell overlay")
