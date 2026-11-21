#!/usr/bin/env python3
"""Install device remarks and mount their control in the HigoOS device cards."""
from pathlib import Path
import sys


def patch(root: Path) -> None:
    sources = Path(__file__).parent
    assets = root / "usr/share/higoros/web/assets"
    pages = list(assets.glob("DevicesPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one DevicesPage asset, found {len(pages)}")
    page = pages[0]
    body = page.read_text(encoding="utf-8")
    edits = (
        ('setup(l,{emit:g}){const a=l,c=g,p=R(l,"selectedType")',
         'setup(l,{emit:g}){const h5000mDeviceRemark=createDeviceRemark({defineComponent:Z,h:Be,ref:M,Modal:N,Button:V,Input:X});const a=l,c=g,p=R(l,"selectedType")'),
        ('e("p",zs,o(t.macAddress),1)',
         'e("p",zs,o(t.macAddress),1),r(h5000mDeviceRemark,{mac:t.macAddress,name:t.name},null,8,["mac","name"])'),
    )
    if all(body.count(old) == 1 and new not in body for old, new in edits):
        for old, new in edits:
            body = body.replace(old, new, 1)
        page.write_text('import{createDeviceRemark}from"./higoos-device-remarks.js";' + body, encoding="utf-8")
    elif not all(body.count(new) == 1 for _, new in edits):
        raise SystemExit("ERROR: HigoOS device card anchors changed")

    body = page.read_text(encoding="utf-8")
    link_setup = 'const h5000mLanLink=createLanLink(Be);'
    if link_setup not in body:
        anchor = 'setup(l,{emit:g}){const h5000mDeviceRemark='
        rate = 'e("span",Ks,o(s(at)(t.connectionDetail)),1)'
        if body.count(anchor) != 1 or body.count(rate) != 1:
            raise SystemExit("ERROR: HigoOS LAN link card anchors changed")
        body = body.replace(anchor, 'setup(l,{emit:g}){' + link_setup + 'const h5000mDeviceRemark=', 1)
        body = body.replace(rate, rate + ',r(h5000mLanLink,{device:t},null,8,["device"])', 1)
        page.write_text('import{createLanLink}from"./higoos-lan-link.js";' + body, encoding="utf-8")

    type_anchor = 'v=A(()=>g.data.value??[])'
    type_replacement = 'v=A(()=>(g.data.value??[]).map(inferDeviceType))'
    body = page.read_text(encoding="utf-8")
    if type_replacement not in body:
        if body.count(type_anchor) != 1:
            raise SystemExit("ERROR: device list type anchor changed")
        body = 'import{inferDeviceType}from"./higoos-device-type.js";' + body.replace(type_anchor, type_replacement, 1)
        page.write_text(body, encoding="utf-8")

    controller = root / "usr/lib/lua/luci/controller/openclash.lua"
    controller_source = controller.read_text(encoding="utf-8")
    route_anchor = 'entry({"admin", "services", "openclash", "backup"}, call("action_backup"))'
    route = 'entry({"admin", "services", "openclash", "device_remarks"}, call("action_higoros_device_remarks"))'
    handler_anchor = "\nfunction action_backup()"
    handler_path = sources / "luci-device-remarks.lua"
    handler = handler_path.read_text(encoding="utf-8")
    if route not in controller_source:
        if controller_source.count(route_anchor) != 1 or controller_source.count(handler_anchor) != 1:
            raise SystemExit("ERROR: OpenClash controller cannot host the device remarks API")
        controller_source = controller_source.replace(route_anchor, route + "\n\t" + route_anchor, 1)
        controller_source = controller_source.replace(handler_anchor, "\n" + handler + handler_anchor, 1)
        controller.write_text(controller_source, encoding="utf-8")
    elif "function action_higoros_device_remarks()" not in controller_source:
        raise SystemExit("ERROR: device remarks route has no handler")
    files = {
        assets / "higoos-lan-link.js": (sources / "higoos-lan-link.js").read_text(encoding="utf-8"),
        assets / "higoos-device-type.js": (sources / "higoos-device-type.js").read_text(encoding="utf-8"),
        assets / "higoos-device-remarks.js": (sources / "higoos-device-remarks.js").read_text(encoding="utf-8"),
        root / "lib/upgrade/keep.d/higoos-device-remarks": "/etc/higoos-device-remarks/\n",
    }
    for path, contents in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    print("PASS: installed independent HigoOS device remarks")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-device-remarks.py ROOTFS_DIR")
    patch(Path(sys.argv[1]))
