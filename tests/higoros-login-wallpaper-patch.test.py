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
        'higoos-login-wallpaper.',
        'wallpaper.value?{backgroundImage:',
        'backgroundSize:"cover"',
        'wallpaper.value?i("img",{src:wallpaper.value',
        'card.style.setProperty("background-color","rgba(255,255,255,.84)"',
        'input[type="password"]',
        'new MutationObserver(q)',
        'style.setProperty("backdrop-filter","blur(12px)")',
    )
    required_native = (
        'localStorage.setItem(key,prefix+encodeURIComponent(selected.name))',
        'localStorage.removeItem("higoos_argon_login_wallpaper_source")',
        'encodeURIComponent(uploadedName)',
        'localStorage.removeItem(key)',
        r'/\.(?:jpe?g|png|gif|webp)$/i',
        'fetch(prefix+encodeURIComponent(selected.name),{cache:"no-store"})',
        'new File([blob],aliasName',
        'localStorage.removeItem("higoos_argon_login_wallpaper_source")',
        'higoos_argon_login_wallpaper_source',
        '背景文件已保存，但同步到 HigoOS 登录页失败',
        'Z(t(s).data.value.files.filter(b=>!b.name.startsWith("higoos-login-wallpaper."))',
    )
    if any(marker not in login_source for marker in required_login):
        raise SystemExit("ERROR: login page does not apply a safe local wallpaper URL")
    if any(marker not in native_source for marker in required_native):
        raise SystemExit("ERROR: Argon file upload/list does not publish a stable login wallpaper")
    if native_source.count('localStorage.removeItem("higoos_argon_login_wallpaper_source")') != 1:
        raise SystemExit("ERROR: repeated patching duplicated or skipped the upload cache reset")
    if not (assets / "higoos-wallpaper-crop.js").is_file():
        raise SystemExit("ERROR: patch did not copy the standalone crop module into web assets")
    upload_handler = native_source[native_source.index('const uploadedName=u.value.name;'):]
    if upload_handler.index('localStorage.removeItem("higoos_argon_login_wallpaper_source")') > upload_handler.index('await l.mutateAsync({file:u.value'):
        raise SystemExit("ERROR: upload cache reset occurs after the file list update")
print("PASS: existing and new Argon uploads publish a stable login wallpaper independent of browser storage")
crop_module = repo / "scripts/higoos-wallpaper-crop.js"
if not crop_module.is_file():
    raise SystemExit("ERROR: standalone HigoOS wallpaper crop module is missing")
crop_source = crop_module.read_text(encoding="utf-8")
required_crop = (
    'mountHigoosWallpaperCrop({upload:file=>l.mutateAsync',
    'higoos-cropped-wallpaper-${Date.now()}.jpg',
    'new MutationObserver(addButtons)',
    '保存裁切并应用',
    'pointermove',
    'canvas.toBlob',
    'await upload(output)',
)
if any(marker not in native_source + crop_source for marker in required_crop):
    raise SystemExit("ERROR: crop controls are not connected to the native upload API")

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    (assets / "OpenClashPage-fixture.js").write_text(
        's("div",bl,[m(i(p),{variant:"secondary",disabled:t.value||!v.value',
        encoding="utf-8",
    )
    (assets / "LuciAppPage-fixture.js").write_text(
        's=l(()=>x(a.value));href:s.value,target:"_blank",rel:"noopener"',
        encoding="utf-8",
    )
    controller = root / "usr/lib/lua/luci/controller/openclash.lua"
    controller.parent.mkdir(parents=True)
    controller.write_text("-- fixture", encoding="utf-8")
    (root / "usr/lib/lua/luci/view/openclash").mkdir(parents=True)
    styles = root / "www/luci-static/resources/openclash/css"
    styles.mkdir(parents=True)
    (styles / "oc-client.css").write_text("", encoding="utf-8")
    (styles / "oc-common.css").write_text("", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(repo / "scripts/patch-higoros-openclash-luci-link.py"), str(root)],
        check=True,
    )
    page = next(assets.glob("OpenClashPage-*.js")).read_text(encoding="utf-8")
    if 'y("iframe",{src:"/cgi-bin/luci/admin/services/openclash"' not in page:
        raise SystemExit("ERROR: native LuCI OpenClash iframe is missing")
    app = next(assets.glob("LuciAppPage-*.js")).read_text(encoding="utf-8")
    if 's=l(()=>JSON.stringify(a.value||{}).toLowerCase().includes("openclash")?"/apps/openclash":x(a.value))' not in app:
        raise SystemExit("ERROR: OpenClash app shortcut does not resolve to the HigoOS route")
    if 'href:s.value,target:JSON.stringify(a.value||{}).toLowerCase().includes("openclash")?"_self":"_blank"' not in app:
        raise SystemExit("ERROR: OpenClash app shortcut does not open in the HigoOS shell")
    if 'e.preventDefault();window.location.assign("/apps/openclash")' not in app:
        raise SystemExit("ERROR: OpenClash launcher has no explicit same-page navigation handler")
    subprocess.run(
        [sys.executable, str(repo / "scripts/patch-higoros-openclash-luci-link.py"), str(root)],
        check=True,
    )
    if next(assets.glob("LuciAppPage-*.js")).read_text(encoding="utf-8") != app:
        raise SystemExit("ERROR: OpenClash shortcut patch is not idempotent")
