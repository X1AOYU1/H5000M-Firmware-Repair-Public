#!/usr/bin/env python3
"""Install device remarks and mount their control in the HigoOS device cards."""
import json
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

    module = "luci.controller.higoos_device_remarks"
    base = "admin/system/higoos-device-remarks"
    routes = {
        base: {"action": {"type": "function", "module": module, "function": "list"}},
        base + "/save": {"action": {"type": "function", "module": module, "function": "save", "post": True}},
    }
    files = {
        assets / "higoos-device-remarks.js": (sources / "higoos-device-remarks.js").read_text(encoding="utf-8"),
        root / "usr/share/ucode/luci/controller/higoos_device_remarks.uc": (sources / "higoos-device-remarks.uc").read_text(encoding="utf-8"),
        root / "usr/share/luci/menu.d/higoos-device-remarks.json": json.dumps(routes, indent=2) + "\n",
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
