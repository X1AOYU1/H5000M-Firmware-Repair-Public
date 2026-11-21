#!/usr/bin/env python3
"""Keep native OpenClash styled and establish its session at HigoOS sign-in."""
from pathlib import Path
import re
import sys


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
    print("PASS: LuCI authenticates through its normal login and native OpenClash ships its page styles")


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
