#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    login = assets / "LoginPage-fixture.js"
    login.write_text(
        'const ue={setup(){const p=M(),x=$(),_=N(),d=a("root"),c=a(""),b=a(!1),f=a(!1),s=a(""),m=a(!1),g=a("--");'
        'F(()=>{x.query.expired==="1"&&(m.value=!0,s.value="会话已过期，请重新登录"),'
        'x.query.changed==="1"&&(m.value=!1,s.value="密码已修改，请使用新密码登录"),H()});'
        'return i("div",Y,[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"})),e("div",{class:"w-full rounded-xl bg-white shadow-lg"},[])])}}',
        encoding="utf-8",
    )
    entry = assets / "index-main-fixture.js"
    entry.write_text('const routes=[DashboardPage,DevicesPage];', encoding="utf-8")
    secondary_entry = assets / "index-secondary-fixture.js"
    secondary_entry.write_text('const widget={name:"other"};', encoding="utf-8")
    native = assets / "NativeConfigSection-fixture.js"
    native.write_text(
        'const{query:s,upload:l,remove:o}=Fe(),v=V(null),u=V(null),i=V(""),y=V(!1),S=V(null),N=V(!1),'
        'g=D(()=>l.isPending.value||o.isPending.value);async function r(){try{await l.mutateAsync('
        '{file:u.value,revision:c?.revision||s.data.value.newRevision}),u.value=null,y.value=!1,v.value&&(v.value.value="")}'
        'catch(d){i.value="failed"}}async function C(){const c=S.value;if(c){try{await o.mutateAsync('
        '{name:c.name,revision:c.revision}),S.value=null,N.value=!1}catch(d){i.value="failed"}}}'
        'Z(t(s).data.value.files,b=>(f(),x("tr"',
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(repo / "scripts/patch-higoros-login-wallpaper.py"), str(root)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(repo / "scripts/patch-higoros-login-wallpaper.py"), str(root)],
        check=True,
    )
    login_source = login.read_text(encoding="utf-8")
    native_source = native.read_text(encoding="utf-8")
    required_login = (
        'localStorage.getItem("higoos_argon_login_wallpaper")',
        '/luci-static/argon/background/',
        'new Image()',
        'style:wallpaper.value?{...Y.style,backgroundImage:',
        'backgroundSize:"cover"',
        'wallpaper.value?i("img",{src:wallpaper.value',
        'h5000m-wallpaper-transparent',
        'new MutationObserver(q)',
        'lightWallpaper=(.2126*d[0]+.7152*d[1]+.0722*d[2])>150',
        'background:rgba(15,23,42,.56)!important;backdrop-filter:blur(14px)!important',
        'background:rgba(255,255,255,.86)!important;backdrop-filter:blur(14px)!important',
        'h5000m-wallpaper-light .login-input{background:rgba(255,255,255,.78)!important',
        'h5000m-wallpaper-light .text-txt-1',
        'html[data-theme="light"] .router-card.login-card.h5000m-wallpaper-transparent',
        'html[data-theme="dark"] .router-card.login-card.h5000m-wallpaper-transparent',
        'if(!wallpaper.value){activeCard?.classList.remove("h5000m-wallpaper-transparent")',
        'backgroundImage:`url("${wallpaper.value}")`',
    )
    required_native = (
        'const current=localStorage.getItem(key),selected=images.find(file=>current===prefix+encodeURIComponent(file.name));',
        'localStorage.removeItem("higoos_argon_login_wallpaper_source")',
        'localStorage.removeItem(key)',
        r'/\.(?:jpe?g|png|gif|webp)$/i',
        'fetch(prefix+encodeURIComponent(selected.name),{cache:"no-store"})',
        'new File([blob],aliasName',
        'localStorage.removeItem("higoos_argon_login_wallpaper_source")',
        'higoos_argon_login_wallpaper_source',
        '背景文件已保存，但同步到 HigoOS 登录页失败',
        'Z(t(s).data.value.files.filter(b=>!b.name.startsWith("higoos-login-wallpaper."))',
    )
    missing_login = [marker for marker in required_login if marker not in login_source]
    if missing_login:
        raise SystemExit(f"ERROR: login page wallpaper integration is missing {missing_login!r}")
    if any(marker not in native_source for marker in required_native):
        raise SystemExit("ERROR: Argon file upload/list does not publish a stable login wallpaper")
    if native_source.count('localStorage.removeItem("higoos_argon_login_wallpaper_source")') != 1:
        raise SystemExit("ERROR: repeated patching duplicated or skipped the upload cache reset")
    if not (assets / "higoos-wallpaper-crop.js").is_file():
        raise SystemExit("ERROR: patch did not copy the standalone crop module into web assets")
    if 'import"./higoos-wallpaper-source.js";' not in entry.read_text(encoding="utf-8"):
        raise SystemExit("ERROR: wallpaper source switching listener is not loaded globally")
    if 'import"./higoos-wallpaper-source.js";' in secondary_entry.read_text(encoding="utf-8"):
        raise SystemExit("ERROR: wallpaper source listener was added to a secondary index bundle")
    source_module = assets / "higoos-wallpaper-source.js"
    if not source_module.is_file() or "clearUploadedWallpaperOnSourceChange" not in source_module.read_text(encoding="utf-8"):
        raise SystemExit("ERROR: choosing another wallpaper source does not clear the upload override")
    if 'images.slice().sort((a,b)=>b.modified-a.modified)[0]' in native_source:
        raise SystemExit("ERROR: newest upload must not be selected automatically")
    if 'localStorage.setItem("higoos_argon_login_wallpaper","/luci-static/argon/background/"+encodeURIComponent(uploadedName))' in native_source:
        raise SystemExit("ERROR: uploading a file must not overwrite the explicit wallpaper selection")
    upload_handler = native_source[native_source.index('const uploadedName=u.value.name;'):]
    if upload_handler.index('localStorage.removeItem("higoos_argon_login_wallpaper_source")') > upload_handler.index('await l.mutateAsync({file:u.value'):
        raise SystemExit("ERROR: upload cache reset occurs after the file list update")
print("PASS: Argon wallpaper files publish safely while explicit selection controls the active login background")
crop_module = repo / "scripts/higoos-wallpaper-crop.js"
if not crop_module.is_file():
    raise SystemExit("ERROR: standalone HigoOS wallpaper crop module is missing")
crop_source = crop_module.read_text(encoding="utf-8")
required_crop = (
    'mountHigoosWallpaperCrop({upload:file=>l.mutateAsync',
    'higoos-cropped-wallpaper-${Date.now()}.jpg',
    '保存裁切并应用',
    'pointermove',
    'canvas.toBlob',
    'await upload(output)',
)
if any(marker not in native_source + crop_source for marker in required_crop):
    raise SystemExit("ERROR: crop controls are not connected to the native upload API")
if '裁切登录壁纸' in crop_source or 'higoos-wallpaper-preview-button' not in crop_source or 'showPreview(name)' not in crop_source:
    raise SystemExit("ERROR: uploaded wallpaper preview must replace the post-upload crop control")
if '设为登录壁纸' not in crop_source or 'localStorage.setItem("higoos_argon_login_wallpaper", prefix + encodeURIComponent(name))' not in crop_source:
    raise SystemExit("ERROR: existing uploaded wallpapers cannot be explicitly selected")
if 'window.higoosCropBeforeUpload(u.value)' not in native_source:
    raise SystemExit("ERROR: wallpaper must be cropped before upload")

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
