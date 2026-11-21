#!/usr/bin/env python3
"""Keep native OpenClash styled and establish its session at HigoOS sign-in."""
from pathlib import Path
import re
import sys


def patch_backup(root: Path, views: Path):
    controller = root / "usr/lib/lua/luci/controller/openclash.lua"
    source = controller.read_text(encoding="utf-8")
    route = ('entry({"admin", "services", "openclash", "backup_upload"}, '
             'post("action_luci_backup_upload")).acl_depends = { "luci-app-openclash" }')
    if route not in source:
        anchor = 'entry({"admin", "services", "openclash", "backup"}, call("action_backup"))'
        old_fn = "function action_higoros_upload()\n"
        old_auth = '\tif not higoros_session_valid() then return respond("error", "HigoOS session is invalid or expired; sign in again") end'
        old_type = '\tlocal upload_type = HTTP.formvalue("upload_type") or ""'
        end = '\nfunction action_backup()'
        if any(source.count(value) != 1 for value in (anchor, old_fn, old_auth, old_type, end)):
            raise SystemExit("ERROR: OpenClash backup upload controller hooks changed")
        source = source.replace(anchor, anchor + "\n\t" + route, 1)
        source = source.replace(old_fn, "local function handle_backup_upload(native)\n", 1)
        source = source.replace(old_auth, old_auth.replace("if not", "if not native and not", 1), 1)
        source = source.replace(old_type, old_type.replace("= HTTP", '= native and "backup-file" or HTTP', 1), 1)
        source = source.replace(end, '\nfunction action_higoros_upload()\n\treturn handle_backup_upload(false)\nend\n'
                                '\nfunction action_luci_backup_upload()\n\treturn handle_backup_upload(true)\nend\n' + end, 1)
        controller.write_text(source, encoding="utf-8")

    # Install with the native templates so the handlers work even when static LuCI assets are unavailable.
    script = Path(__file__).with_name("luci-openclash-backup.js").read_text(encoding="utf-8")
    tag = (
        '<script id="h5000m-native-backup" '
        'data-endpoint="<%=pcdata(luci.dispatcher.build_url(\'admin\', \'services\', \'openclash\', \'backup_upload\'))%>" '
        'data-token="<%=pcdata(luci.dispatcher.context.authtoken or \'\')%>">\n' + script + '</script>\n'
    )
    for filename, button in (("upload.htm", 'id="upload-submit"'), ("status.htm", 'id="restore_backup_large"')):
        view = views / filename
        body = view.read_text(encoding="utf-8")
        if body.count(button) != 1:
            raise SystemExit(f"ERROR: native OpenClash restore control changed: {filename}")
        if 'id="h5000m-native-backup"' not in body:
            view.write_text(body + "\n" + tag, encoding="utf-8")


def patch_update_return(root: Path):
    model = root / "usr/lib/lua/luci/model/cbi/openclash/settings.lua"
    source = model.read_text(encoding="utf-8")
    redirect = 'HTTP.redirect(DISP.build_url("admin", "services", "openclash"))'
    stay = 'HTTP.redirect(DISP.build_url("admin", "services", "openclash", "settings"))'
    for command in (*(f"openclash_geo.sh {name}" for name in ("ipdb", "geoip", "geosite", "geoasn")), "openclash_chnroute.sh"):
        queue = f'SYS.call("/usr/share/openclash/{command} >/dev/null 2>&1 &")'
        anchor = queue + "\n\t" + redirect
        updated = queue + "\n\t" + stay
        if source.count(anchor) == 1:
            source = source.replace(anchor, updated, 1)
        elif source.count(updated) != 1:
            raise SystemExit(f"ERROR: native OpenClash update action changed: {command}")
    model.write_text(source, encoding="utf-8")


def patch(root: Path):
    web = root / "usr/share/higoros/web"
    assets = web / "assets"
    router = [p for p in (web / "assets").glob("index-*.js") if '"/auth/login"' in p.read_text(encoding="utf-8")]
    if len(router) != 1:
        raise SystemExit("ERROR: expected one HigoOS authentication bundle")
    bundle = router[0]
    source = bundle.read_text(encoding="utf-8")
    login = 'await kn.login(u,d),await e.invalidateQueries({queryKey:lt.me()})'
    logout = 'try{await kn.logout()}catch{}await e.invalidateQueries({queryKey:lt.me()}),Wn()'
    establish = (
        'await kn.login(u,d);if(u==="root")try{await fetch("/cgi-bin/luci/admin",'
        '{method:"POST",credentials:"same-origin",redirect:"manual",cache:"no-store",'
        'signal:AbortSignal.timeout(5000),body:new URLSearchParams({luci_username:u,luci_password:d})})}catch{}'
        'await e.invalidateQueries({queryKey:lt.me()})'
    )
    destroy = (
        'try{await fetch("/cgi-bin/luci/admin/logout",{credentials:"same-origin",redirect:"manual",'
        'cache:"no-store",signal:AbortSignal.timeout(3000)})}catch{}'
    )
    if establish not in source:
        if source.count(login) != 1 or source.count(logout) != 1:
            raise SystemExit("ERROR: HigoOS sign-in/sign-out hooks changed")
        source = source.replace(login, establish, 1).replace(
            logout, destroy + logout, 1
        )
    route = '{path:"apps/openclash-luci",component:()=>import("./higoos-native-openclash.js"),meta:{title:"OpenClash"}},'
    if route not in source:
        anchor = '{path:"apps/openclash",'
        if source.count(anchor) != 1:
            raise SystemExit("ERROR: HigoOS OpenClash router hook changed")
        source = source.replace(anchor, route + anchor, 1)
    bundle.write_text(source, encoding="utf-8")
    vendors = sorted(assets.glob("vendor-*.js"))
    if len(vendors) != 1:
        raise SystemExit("ERROR: expected one HigoOS Vue bundle")
    frame_module = Path(__file__).with_name("higoos-native-openclash.js").read_text(encoding="utf-8")
    (assets / "higoos-native-openclash.js").write_text(
        frame_module.replace("./__vue_bundle__.js", "./" + vendors[0].name), encoding="utf-8"
    )

    css_dir = root / "www/luci-static/resources/openclash/css"
    views = root / "usr/lib/lua/luci/view/openclash"
    marker = re.compile(
        r'<link\s+rel="stylesheet"\s+href="/luci-static/resources/openclash/css/'
        r'(oc-[a-z0-9-]+\.css)(?:\?[^"]*)?"\s*/?>'
    )
    for view in views.glob("*.htm"):
        current = view.read_text(encoding="utf-8")

        def inline(match):
            name = match[1]
            css = (css_dir / name).read_text(encoding="utf-8")
            if not css.strip() or re.search(r'</style|<%|@import', css, re.I):
                raise SystemExit(f"ERROR: cannot inline native OpenClash stylesheet {name}")
            return f'<style data-openclash-style="{name}">\n{css}\n</style>'

        updated = marker.sub(inline, current)
        if updated != current:
            view.write_text(updated, encoding="utf-8")

    status = (views / "status.htm").read_text(encoding="utf-8")
    if not all(f'data-openclash-style="{name}"' in status for name in ("oc-common.css", "oc-client.css")):
        raise SystemExit("ERROR: native OpenClash status styles are missing")
    patch_backup(root, views)
    patch_update_return(root)
    print("PASS: native GEO and China route updates return to the settings page")
    print("PASS: native OpenClash backup forms use the authenticated LuCI chunk upload route")
    print("PASS: LuCI authenticates through its normal login and native OpenClash ships its page styles")


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
