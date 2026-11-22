#!/usr/bin/env python3
"""Apply uploaded Argon image backgrounds to the HigoOS SPA login page."""
from pathlib import Path
import sys


root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
login_pages = sorted(assets.glob("LoginPage-*.js"))
native_pages = sorted(assets.glob("NativeConfigSection*.js"))
if len(login_pages) != 1 or len(native_pages) != 1:
    raise SystemExit(
        f"ERROR: expected one HigoOS login page and native settings bundle; "
        f"found {len(login_pages)} and {len(native_pages)}"
    )

login_path = login_pages[0]
login = login_path.read_text(encoding="utf-8")
entry_pages = sorted(assets.glob("index-*.js"))
entry_candidates = [
    path for path in entry_pages
    if "DashboardPage" in path.read_text(encoding="utf-8")
    and "DevicesPage" in path.read_text(encoding="utf-8")
]
if len(entry_candidates) != 1:
    raise SystemExit(
        f"ERROR: expected one HigoOS SPA router entry bundle, found {len(entry_candidates)} "
        f"among {len(entry_pages)} index bundles"
    )
entry_path = entry_candidates[0]
entry = entry_path.read_text(encoding="utf-8")
source_import = 'import"./higoos-wallpaper-source.js";'
if source_import not in entry:
    entry = source_import + entry
source_path = assets / "higoos-wallpaper-source.js"
source_code = Path(__file__).with_name("higoos-wallpaper-source.js").read_text(encoding="utf-8")
source_path.write_text(source_code, encoding="utf-8")
entry_path.write_text(entry, encoding="utf-8")
setup_anchor = 'd=a("root"),c=a(""),b=a(!1)'
setup_replacement = 'd=a("root"),wallpaper=a(""),c=a(""),b=a(!1)'
if login.count(setup_anchor) == 1:
    login = login.replace(setup_anchor, setup_replacement, 1)
elif 'd=a("root"),wallpaper=a(""),c=a("")' not in login:
    raise SystemExit("ERROR: HigoOS login state anchor changed")

mounted_anchor = 'x.query.changed==="1"&&(m.value=!1,s.value="密码已修改，请使用新密码登录"),H()'
login_probe = (
    '(()=>{const p=[];try{const w=localStorage.getItem("higoos_argon_login_wallpaper");'
    'if(w&&w.startsWith("/luci-static/argon/background/"))p.push(w)}catch{}'
    'const n=()=>{const w=p.shift();if(!w)return;const image=new Image();image.onload=()=>{try{const c=document.createElement("canvas");'
    'c.width=c.height=1;const x=c.getContext("2d");x.drawImage(image,0,0,1,1);const d=x.getImageData(0,0,1,1).data;'
    'lightWallpaper=(.2126*d[0]+.7152*d[1]+.0722*d[2])>150}catch{lightWallpaper=false}wallpaper.value=w+"?v="+Date.now()};'
    'image.onerror=n;image.src=w+"?v="+Date.now()};n();let mo,activeCard,styleTag,lightWallpaper=false;const q=()=>{'
    'if(!wallpaper.value){activeCard?.classList.remove("h5000m-wallpaper-transparent");'
    'document.querySelector(".min-h-screen.h5000m-wallpaper-active")?.classList.remove("h5000m-wallpaper-active","h5000m-wallpaper-light");styleTag?.remove();'
    'activeCard=null;styleTag=null;return}const card=document.querySelector(".router-card.login-card");if(!card)return;'
    'const page=card.closest(".min-h-screen");'
    'if(!styleTag){styleTag=document.createElement("style");styleTag.textContent='
    '\'html[data-theme="light"] .router-card.login-card.h5000m-wallpaper-transparent,'+
    'html[data-theme="light"] .router-card.login-card.h5000m-wallpaper-transparent:before,'+
    'html[data-theme="light"] .router-card.login-card.h5000m-wallpaper-transparent:after,'+
    'html[data-theme="dark"] .router-card.login-card.h5000m-wallpaper-transparent,'+
    'html[data-theme="dark"] .router-card.login-card.h5000m-wallpaper-transparent:before,'+
    'html[data-theme="dark"] .router-card.login-card.h5000m-wallpaper-transparent:after{'
    'background:transparent!important;background-image:none!important;backdrop-filter:none!important;'
    '-webkit-backdrop-filter:none!important;border-color:transparent!important;box-shadow:none!important}'
    '.router-card.login-card.h5000m-wallpaper-transparent:before,'+
    '.router-card.login-card.h5000m-wallpaper-transparent:after,'+
    '.h5000m-wallpaper-active .login-glow{display:none!important}\';'
    'styleTag.textContent+=\'html[data-theme="light"] .h5000m-wallpaper-active .router-card.login-card.h5000m-wallpaper-transparent,'+
    'html[data-theme="dark"] .h5000m-wallpaper-active .router-card.login-card.h5000m-wallpaper-transparent{'
    'background:rgba(15,23,42,.56)!important;backdrop-filter:blur(14px)!important;'
    '-webkit-backdrop-filter:blur(14px)!important;border-color:rgba(255,255,255,.22)!important;'
    'box-shadow:0 12px 40px #0005!important}'+
    'html[data-theme="light"] .h5000m-wallpaper-active.h5000m-wallpaper-light .router-card.login-card.h5000m-wallpaper-transparent{'
    'background:rgba(255,255,255,.86)!important;backdrop-filter:blur(14px)!important;'
    '-webkit-backdrop-filter:blur(14px)!important;border-color:rgba(15,23,42,.22)!important;'
    'box-shadow:0 12px 40px #0f172a35!important}\';'
    'styleTag.textContent+=\' .h5000m-wallpaper-active .text-txt-1,'+
    '.h5000m-wallpaper-active .text-txt-2,.h5000m-wallpaper-active .text-txt-4{color:#fff!important;'+
    'text-shadow:0 1px 2px #000b}'+
    '.h5000m-wallpaper-active .login-input{background:transparent!important;'+
    'color:#fff!important;border-color:rgba(255,255,255,.55)!important;text-shadow:0 1px 3px #000,0 0 5px #000!important}'+
    'html[data-theme="light"] .h5000m-wallpaper-active .login-input{background:transparent!important;'+
    'text-shadow:0 1px 3px #000,0 0 5px #000!important}'+
    '.h5000m-wallpaper-active .login-input::placeholder{color:#d1d5db!important;opacity:1}'+
    '.h5000m-wallpaper-active .login-input:focus{outline:2px solid #fff!important;outline-offset:2px}'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .text-txt-1,'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .text-txt-2,'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .text-txt-4{color:#172033!important;text-shadow:0 1px 2px #fff!important}'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .login-input{background:rgba(255,255,255,.78)!important;'
    'color:#111827!important;border-color:rgba(15,23,42,.55)!important;text-shadow:none!important}'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .login-input::placeholder{color:#475569!important;opacity:1}'+
    '.h5000m-wallpaper-active.h5000m-wallpaper-light .login-input:focus{outline:2px solid #2563eb!important;outline-offset:2px}\';'
    'document.head.append(styleTag)}if(activeCard&&activeCard!==card)activeCard.classList.remove("h5000m-wallpaper-transparent");'
    'activeCard=card;card.classList.add("h5000m-wallpaper-transparent");page?.classList.add("h5000m-wallpaper-active");'
    'page?.classList.toggle("h5000m-wallpaper-light",lightWallpaper)};q();'
    'mo=new MutationObserver(q);mo.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:["data-theme"]})})()'
)
mounted_replacement = (
    'x.query.changed==="1"&&(m.value=!1,s.value="密码已修改，请使用新密码登录"),'
    + login_probe + ',H()'
)
if login.count(mounted_anchor) == 1:
    login = login.replace(mounted_anchor, mounted_replacement, 1)
elif login_probe in login:
    pass
elif 'localStorage.getItem("higoos_argon_login_wallpaper")' in login:
    wallpaper_marker = login.index('localStorage.getItem("higoos_argon_login_wallpaper")')
    mounted_start = login.rfind('(()=>{', 0, wallpaper_marker)
    if mounted_start < 0:
        raise SystemExit("ERROR: HigoOS login wallpaper probe wrapper changed")
    mounted_end = login.index('})(),H()', mounted_start) + len('})(),H()')
    login = login[:mounted_start] + login_probe + ',H()' + login[mounted_end:]
else:
    raise SystemExit("ERROR: HigoOS login mount hook changed")

root_anchor = 'i("div",Y,[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
root_replacement = (
    'i("div",{...Y,style:wallpaper.value?{...Y.style,backgroundImage:`url("${wallpaper.value}")`,'
    'backgroundSize:"cover",backgroundPosition:"center"}:Y.style},'
    '[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
)
if login.count(root_anchor) == 1:
    login = login.replace(root_anchor, root_replacement, 1)
elif 'backgroundImage:`linear-gradient(rgba(15,23,42,.46),rgba(15,23,42,.62)),url("${wallpaper.value}")`' in login:
    login = login.replace('backgroundImage:`linear-gradient(rgba(15,23,42,.46),rgba(15,23,42,.62)),url("${wallpaper.value}")`', 'backgroundImage:`url("${wallpaper.value}")`', 1)
elif 'style:wallpaper.value?{...Y.style,backgroundImage:' not in login:
    old_root = 'i("div",{...Y,style:wallpaper.value?{backgroundImage:`url("${wallpaper.value}")`,backgroundSize:"cover",backgroundPosition:"center"}:void 0},'
    if old_root in login:
        login = login.replace(old_root, 'i("div",{...Y,style:wallpaper.value?{...Y.style,backgroundImage:`url("${wallpaper.value}")`,backgroundSize:"cover",backgroundPosition:"center"}:Y.style},', 1)
    elif 'wallpaper.value?{backgroundImage:' not in login:
        raise SystemExit("ERROR: HigoOS login root element changed")
image_anchor = ',[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
image_replacement = (
    ',[wallpaper.value?i("img",{src:wallpaper.value,alt:"",class:"absolute inset-0 h-full w-full '
    'object-cover pointer-events-none"},null,8,["src"]):z("",!0),t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
)
if login.count(image_anchor) == 1:
    login = login.replace(image_anchor, image_replacement, 1)
elif 'wallpaper.value?i("img",{src:wallpaper.value' not in login:
    raise SystemExit("ERROR: HigoOS login background image insertion point changed")
login_path.write_text(login, encoding="utf-8")

native_path = native_pages[0]
native = native_path.read_text(encoding="utf-8")
crop_module = assets / "higoos-wallpaper-crop.js"
crop_source = Path(__file__).with_name("higoos-wallpaper-crop.js").read_text(encoding="utf-8")
crop_import = 'import{mountHigoosWallpaperCrop}from"./higoos-wallpaper-crop.js";'
if crop_import not in native:
    native = crop_import + native
crop_module.write_text(crop_source, encoding="utf-8")
files_anchor = 'const{query:s,upload:l,remove:o}=Fe(),v=V(null)'
files_replacement = 'const{query:s,upload:l,remove:o}=Fe(),v=V(null)'
if native.count(files_anchor) != 1:
    raise SystemExit("ERROR: Argon background component anchor changed")

# Keep a browser-local fallback and publish the selected upload under a stable
# public name so the login page can find it without relying on local storage.
query_watch_anchor = 'g=D(()=>l.isPending.value||o.isPending.value);async function r()'
query_watch_replacement = (
    'g=D(()=>l.isPending.value||o.isPending.value);let publishing="";'
    'ee(()=>s.data.value?.files,async files=>{if(!Array.isArray(files)||publishing)return;const key="higoos_argon_login_wallpaper",'
    'sourceKey="higoos_argon_login_wallpaper_source",prefix="/luci-static/argon/background/",'
    'images=files.filter(file=>/\\.(?:jpe?g|png|gif|webp)$/i.test(file.name)&&!file.name.startsWith("higoos-login-wallpaper.")),'
    'aliases=files.filter(file=>file.name.startsWith("higoos-login-wallpaper."));try{'
    'if(!images.length){localStorage.removeItem(key);localStorage.removeItem(sourceKey);if(aliases.length){publishing="clear";'
    'try{for(const file of aliases)await o.mutateAsync({name:file.name,revision:file.revision})}finally{publishing=""}}return}'
    'const current=localStorage.getItem(key),selected=images.find(file=>current===prefix+encodeURIComponent(file.name));'
    'if(!selected){localStorage.removeItem(sourceKey);return}const extension=selected.name.split(".").pop().toLowerCase(),'
    'aliasName="higoos-login-wallpaper."+extension;'
    'if(localStorage.getItem(sourceKey)===selected.name&&aliases.some(file=>file.name===aliasName))return;'
    'publishing=selected.name;'
    'for(const file of aliases)await o.mutateAsync({name:file.name,revision:file.revision});'
    'const response=await fetch(prefix+encodeURIComponent(selected.name),{cache:"no-store"});'
    'if(!response.ok)throw new Error("background fetch failed");const blob=await response.blob(),'
    'copy=new File([blob],aliasName,{type:blob.type||"image/"+extension}),state=s.data.value;'
    'await l.mutateAsync({file:copy,revision:state?.newRevision});localStorage.setItem(sourceKey,selected.name);publishing=""'
    '}catch(error){publishing="";i.value="背景文件已保存，但同步到 HigoOS 登录页失败，请刷新或重新上传";'
    'console.error("Failed to publish HigoOS login wallpaper:",error)}},{immediate:true});'
    'async function r()'
)
if native.count(query_watch_anchor) == 1:
    native = native.replace(query_watch_anchor, query_watch_replacement, 1)
elif 'let publishing=""' in native and 'higoos_argon_login_wallpaper_source' in native:
    pass
elif 'g=D(()=>l.isPending.value||o.isPending.value);ee(()=>s.data.value?.files,files=>' in native:
    watcher_start = native.index('g=D(()=>l.isPending.value||o.isPending.value);')
    watcher_end = native.index('async function r()', watcher_start) + len('async function r()')
    native = native[:watcher_start] + query_watch_replacement + native[watcher_end:]
else:
    raise SystemExit("ERROR: Argon background list watcher anchor changed")

crop_call = 'mountHigoosWallpaperCrop({upload:file=>l.mutateAsync({file,revision:s.data.value?.newRevision})});'
if crop_call not in native:
    crop_anchor = 'async function r()'
    if native.count(crop_anchor) != 1:
        raise SystemExit("ERROR: Argon background upload function anchor changed")
    native = native.replace(crop_anchor, crop_call + crop_anchor, 1)

upload_anchor = 'try{await l.mutateAsync({file:u.value,revision:c?.revision||s.data.value.newRevision}),u.value=null'
upload_replacement = (
    'try{const cropped=await window.higoosCropBeforeUpload(u.value);if(!cropped)return;u.value=cropped;const uploadedName=u.value.name;try{localStorage.removeItem("higoos_argon_login_wallpaper_source")}catch{}'
    'await l.mutateAsync({file:u.value,revision:s.data.value.files.find(d=>d.name===uploadedName)?.revision||s.data.value.newRevision});'
    'u.value=null'
)
if native.count(upload_anchor) == 1:
    native = native.replace(upload_anchor, upload_replacement, 1)
elif 'const uploadedName=u.value.name;' in native and 'window.higoosCropBeforeUpload(u.value)' not in native:
    native = native.replace('try{const uploadedName=u.value.name;', 'try{const cropped=await window.higoosCropBeforeUpload(u.value);if(!cropped)return;u.value=cropped;const uploadedName=u.value.name;', 1)
elif 'const uploadedName=u.value.name;' not in native:
    raise SystemExit("ERROR: Argon background upload success handler changed")
cache_reset = 'localStorage.removeItem("higoos_argon_login_wallpaper_source")'
handler_start = native.find('const uploadedName=u.value.name;')
mutate_at = native.find('await l.mutateAsync({file:u.value', handler_start)
reset_at = native.find(cache_reset, handler_start) if handler_start >= 0 else -1
if handler_start < 0 or mutate_at < 0:
    raise SystemExit("ERROR: Argon background upload handler changed")
if reset_at < 0 or reset_at > mutate_at:
    if reset_at >= 0:
        native = native[:reset_at] + native[reset_at + len(cache_reset):]
        handler_start = native.find('const uploadedName=u.value.name;')
        mutate_at = native.find('await l.mutateAsync({file:u.value', handler_start)
    native = native[:mutate_at] + 'try{' + cache_reset + '}catch{}' + native[mutate_at:]
if 'localStorage.removeItem("higoos_argon_login_wallpaper_source")' not in native:
    publish_marker = 'localStorage.setItem("higoos_argon_login_wallpaper","/luci-static/argon/background/"+encodeURIComponent(uploadedName))'
    if native.count(publish_marker) != 1:
        raise SystemExit("ERROR: Argon upload wallpaper selection marker changed")
    native = native.replace(
        publish_marker,
        publish_marker + ';localStorage.removeItem("higoos_argon_login_wallpaper_source")',
        1,
    )

delete_anchor = 'await o.mutateAsync({name:c.name,revision:c.revision}),S.value=null'
delete_replacement = (
    'await o.mutateAsync({name:c.name,revision:c.revision});try{const key="higoos_argon_login_wallpaper",'
    'prefix="/luci-static/argon/background/";if(localStorage.getItem(key)===prefix+encodeURIComponent(c.name))'
    'localStorage.removeItem(key)}catch{}S.value=null'
)
if native.count(delete_anchor) == 1:
    native = native.replace(delete_anchor, delete_replacement, 1)
elif 'localStorage.getItem(key)===prefix+encodeURIComponent(c.name)' not in native:
    raise SystemExit("ERROR: Argon background delete success handler changed")

table_anchor = 'Z(t(s).data.value.files,b=>(f(),x("tr"'
table_replacement = 'Z(t(s).data.value.files.filter(b=>!b.name.startsWith("higoos-login-wallpaper.")),b=>(f(),x("tr"'
if native.count(table_anchor) == 1:
    native = native.replace(table_anchor, table_replacement, 1)
elif table_replacement not in native:
    raise SystemExit("ERROR: Argon background file table changed")
native_path.write_text(native, encoding="utf-8")

for marker, content in (
    ("new Image()", login),
    ('h5000m-wallpaper-transparent', login),
    ('backgroundImage:`url("${wallpaper.value}")`', login),
    ('wallpaper.value?i("img",{src:wallpaper.value', login),
    ("/luci-static/argon/background/", native),
    ('"higoos_argon_login_wallpaper_source"', native),
    ("new File([blob],aliasName", native),
    ("mountHigoosWallpaperCrop({upload:file=>l.mutateAsync", native),
    ('import"./higoos-wallpaper-source.js";', entry),
    ("clearUploadedWallpaperOnSourceChange", source_code),
    ("export function mountHigoosWallpaperCrop", crop_source),
    ('files.filter(b=>!b.name.startsWith("higoos-login-wallpaper."))', native),
):
    if marker not in content:
        raise SystemExit(f"ERROR: login wallpaper integration missing {marker}")
print("PASS: HigoOS login probes a stable Argon background path; crop output uploads through the native Argon API")
