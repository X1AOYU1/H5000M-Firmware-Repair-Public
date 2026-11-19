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
overlay_handler = (
    '(()=>{if(window.__higoosOpenClashFrame)return;'
    'window.__higoosOpenClashFrame=true;'
    'document.addEventListener("click",e=>{'
    'const t=e.target instanceof Element?e.target:null;'
    'const control=t&&t.closest("a,button");if(!control)return;'
    'let card=control,matched=false;'
    'for(let i=0;card&&i<8;i++,card=card.parentElement){'
    'const text=(card.innerText||card.textContent||"").toLowerCase();'
    'if(text.includes("openclash")&&text.includes("打开")){matched=true;break}}'
    'if(!matched)return;e.preventDefault();e.stopImmediatePropagation();'
    'if(document.getElementById("higoos-openclash-frame"))return;'
    'const overlay=document.createElement("div");overlay.id="higoos-openclash-frame";'
    'Object.assign(overlay.style,{position:"fixed",inset:"0",zIndex:"2147483000",'
    'background:"#f3f5f8",display:"flex",flexDirection:"column"});'
    'const bar=document.createElement("div");Object.assign(bar.style,{height:"48px",'
    'flex:"0 0 48px",display:"flex",alignItems:"center",justifyContent:"space-between",'
    'padding:"0 16px",background:"#fff",borderBottom:"1px solid #d9dee8",font:"14px sans-serif"});'
    'const title=document.createElement("strong");title.textContent="OpenClash";'
    'const close=document.createElement("button");close.type="button";close.textContent="关闭";'
    'Object.assign(close.style,{padding:"6px 12px",cursor:"pointer"});'
    'close.addEventListener("click",()=>overlay.remove());bar.append(title,close);'
    'const frame=document.createElement("iframe");frame.title="LuCI OpenClash";'
    'frame.src="/cgi-bin/luci/admin/services/openclash";'
    'Object.assign(frame.style,{width:"100%",height:"calc(100% - 48px)",flex:"1",border:"0",background:"#fff"});'
    'overlay.append(bar,frame);document.body.append(overlay)},true)})();'
)
if "window.__higoosOpenClashFrame" not in app_source:
    app_source += overlay_handler
app_path.write_text(app_source, encoding="utf-8")
if 'document.addEventListener("click"' not in app_source or 'frame.src="/cgi-bin/luci/admin/services/openclash"' not in app_source:
    raise SystemExit("ERROR: OpenClash app center button does not open the embedded LuCI interface")
print("PASS: OpenClash app center clicks open native LuCI in an in-shell overlay")
