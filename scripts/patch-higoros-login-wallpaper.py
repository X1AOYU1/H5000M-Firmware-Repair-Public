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
    'p.push(...["webp","png","jpg","jpeg","gif"].map(e=>"/luci-static/argon/background/higoos-login-wallpaper."+e));'
    'const n=()=>{const w=p.shift();if(!w)return;const image=new Image();image.onload=()=>wallpaper.value=w+"?v="+Date.now();'
    'image.onerror=n;image.src=w+"?v="+Date.now()};n()})()'
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
    mounted_start = login.index('(()=>{try{const w=localStorage.getItem("higoos_argon_login_wallpaper")')
    mounted_end = login.index('})(),H()', mounted_start) + len('})(),H()')
    login = login[:mounted_start] + login_probe + ',H()' + login[mounted_end:]
else:
    raise SystemExit("ERROR: HigoOS login mount hook changed")

root_anchor = 'i("div",Y,[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
root_replacement = (
    'i("div",{...Y,style:wallpaper.value?{backgroundImage:`linear-gradient('
    'rgba(15,23,42,.46),rgba(15,23,42,.62)),url("${wallpaper.value}")`,'
    'backgroundSize:"cover",backgroundPosition:"center"}:void 0},'
    '[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}'
)
if login.count(root_anchor) == 1:
    login = login.replace(root_anchor, root_replacement, 1)
elif 'wallpaper.value?{backgroundImage:' not in login:
    raise SystemExit("ERROR: HigoOS login root element changed")
login_path.write_text(login, encoding="utf-8")

native_path = native_pages[0]
native = native_path.read_text(encoding="utf-8")
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
    'const current=localStorage.getItem(key),selected=images.find(file=>current===prefix+encodeURIComponent(file.name))'
    '||images.slice().sort((a,b)=>b.modified-a.modified)[0],extension=selected.name.split(".").pop().toLowerCase(),'
    'aliasName="higoos-login-wallpaper."+extension;localStorage.setItem(key,prefix+encodeURIComponent(selected.name));'
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

upload_anchor = 'try{await l.mutateAsync({file:u.value,revision:c?.revision||s.data.value.newRevision}),u.value=null'
upload_replacement = (
    'try{const uploadedName=u.value.name;await l.mutateAsync({file:u.value,revision:c?.revision||s.data.value.newRevision});'
    'try{if(/\\.(?:jpe?g|png|gif|webp)$/i.test(uploadedName))localStorage.setItem('
    '"higoos_argon_login_wallpaper","/luci-static/argon/background/"+encodeURIComponent(uploadedName));'
    'localStorage.removeItem("higoos_argon_login_wallpaper_source")}catch{}'
    'u.value=null'
)
if native.count(upload_anchor) == 1:
    native = native.replace(upload_anchor, upload_replacement, 1)
elif 'const uploadedName=u.value.name;await l.mutateAsync' not in native:
    raise SystemExit("ERROR: Argon background upload success handler changed")
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
    ("higoos-login-wallpaper.", login),
    ("/luci-static/argon/background/", native),
    ('"higoos_argon_login_wallpaper_source"', native),
    ("new File([blob],aliasName", native),
    ('files.filter(b=>!b.name.startsWith("higoos-login-wallpaper."))', native),
):
    if marker not in content:
        raise SystemExit(f"ERROR: login wallpaper integration missing {marker}")
print("PASS: HigoOS login probes a stable Argon background path; existing and new uploads publish there")
