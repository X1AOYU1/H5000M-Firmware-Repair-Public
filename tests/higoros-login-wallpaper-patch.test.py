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
        'return i("div",Y,[t[11]||(t[11]=e("div",{class:"absolute inset-0 overflow-hidden"}))])}}',
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
    login_source = login.read_text(encoding="utf-8")
    native_source = native.read_text(encoding="utf-8")
    required_login = (
        'localStorage.getItem("higoos_argon_login_wallpaper")',
        '/luci-static/argon/background/',
        'new Image()',
        'higoos-login-wallpaper.',
        'wallpaper.value?{backgroundImage:',
        'backgroundSize:"cover"',
    )
    required_native = (
        'localStorage.setItem(key,prefix+encodeURIComponent(selected.name))',
        'encodeURIComponent(uploadedName)',
        'localStorage.removeItem(key)',
        r'/\.(?:jpe?g|png|gif|webp)$/i',
        'fetch(prefix+encodeURIComponent(selected.name),{cache:"no-store"})',
        'new File([blob],aliasName',
        'higoos_argon_login_wallpaper_source',
        '背景文件已保存，但同步到 HigoOS 登录页失败',
        'Z(t(s).data.value.files.filter(b=>!b.name.startsWith("higoos-login-wallpaper."))',
    )
    if any(marker not in login_source for marker in required_login):
        raise SystemExit("ERROR: login page does not apply a safe local wallpaper URL")
    if any(marker not in native_source for marker in required_native):
        raise SystemExit("ERROR: Argon file upload/list does not publish a stable login wallpaper")
print("PASS: existing and new Argon uploads publish a stable login wallpaper independent of browser storage")
