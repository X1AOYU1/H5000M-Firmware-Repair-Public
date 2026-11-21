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
    elif not (body.count('const h5000mDeviceRemark=createDeviceRemark({defineComponent:Z,h:Be,ref:M,Modal:N,Button:V,Input:X})') == 1 and body.count('r(h5000mDeviceRemark,{mac:t.macAddress,name:t.name},null,8,["mac","name"])') == 1):
        raise SystemExit("ERROR: HigoOS device card anchors changed")

    body = page.read_text(encoding="utf-8")
    vendor_setup = 'const h5000mDeviceVendor=createDeviceVendor({defineComponent:Z,h:Be,ref:M});'
    vendor_card = 'r(h5000mDeviceVendor,{mac:t.macAddress,class:zs.class},null,8,["mac"])'
    if vendor_setup not in body:
        anchor = 'setup(l,{emit:g}){const h5000mDeviceRemark='
        if anchor not in body:
            anchor = 'setup(l,{emit:g}){const h5000mLanLink=createLanLink(Be);const h5000mDeviceRemark='
        card = 'e("p",zs,o(t.macAddress),1)'
        if body.count(anchor) != 1 or body.count(card) != 1:
            raise SystemExit("ERROR: device vendor card anchors changed")
        body = 'import{createDeviceVendor}from"./higoos-device-vendor.js";' + body.replace(anchor, anchor.replace('const h5000mDeviceRemark=', vendor_setup + 'const h5000mDeviceRemark='), 1).replace(card, card + ',' + vendor_card, 1)
        page.write_text(body, encoding="utf-8")

    body = page.read_text(encoding="utf-8")
    avatar_setup = 'const h5000mDeviceAvatar=createDeviceAvatar({defineComponent:Z,h:Be,ref:M});'
    avatar = 'e("img",{src:s(de)(t.osType),alt:"",class:"w-6 h-6 object-contain"},null,8,Bs)'
    if avatar_setup not in body:
        if body.count(vendor_setup) != 1 or body.count(avatar) != 1:
            raise SystemExit("ERROR: HigoOS device avatar anchors changed")
        body = body.replace('import{createDeviceVendor}from', 'import{createDeviceVendor,createDeviceAvatar}from', 1)
        body = body.replace(vendor_setup, vendor_setup + avatar_setup, 1)
        body = body.replace(avatar, 'r(h5000mDeviceAvatar,{mac:t.macAddress,name:t.name,fallback:s(de)(t.osType)},null,8,["mac","name","fallback"])', 1)
        page.write_text(body, encoding="utf-8")

    body = page.read_text(encoding="utf-8")
    old_avatar = 'r(h5000mDeviceAvatar,{mac:t.macAddress,fallback:s(de)(t.osType)},null,8,["mac","fallback"])'
    new_avatar = 'r(h5000mDeviceAvatar,{mac:t.macAddress,name:t.name,fallback:s(de)(t.osType)},null,8,["mac","name","fallback"])'
    if old_avatar in body:
        body = body.replace(old_avatar, new_avatar, 1)
        page.write_text(body, encoding="utf-8")
    elif body.count(new_avatar) != 1:
        raise SystemExit("ERROR: HigoOS device avatar name anchor changed")

    body = page.read_text(encoding="utf-8")
    avatar_box = 'Ps={class:"w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-bg-1/60 border border-line-1/70"}'
    avatar_box_large = avatar_box.replace('w-12 h-12', 'w-14 h-14')
    if avatar_box_large not in body:
        if body.count(avatar_box) != 1:
            raise SystemExit("ERROR: device avatar box anchor changed")
        body = body.replace(avatar_box, avatar_box_large, 1)
        page.write_text(body, encoding="utf-8")

    body = page.read_text(encoding="utf-8")
    link_setup = 'const h5000mLanLink=createLanLink(Be);'
    if link_setup not in body:
        anchor = 'setup(l,{emit:g}){' + vendor_setup + avatar_setup + 'const h5000mDeviceRemark='
        rate = 'e("span",Ks,o(s(at)(t.connectionDetail)),1)'
        if body.count(anchor) != 1 or body.count(rate) != 1:
            raise SystemExit("ERROR: HigoOS LAN link card anchors changed")
        body = body.replace(anchor, 'setup(l,{emit:g}){' + link_setup + vendor_setup + avatar_setup + 'const h5000mDeviceRemark=', 1)
        body = body.replace(rate, 'r(h5000mLanLink,{device:t,fallback:s(at)(t.connectionDetail)},null,8,["device","fallback"])', 1)
        page.write_text('import{createLanLink}from"./higoos-lan-link.js";' + body, encoding="utf-8")

    type_anchor = 'v=A(()=>g.data.value??[])'
    type_replacement = 'v=A(()=>(g.data.value??[]).map(inferDeviceType))'
    body = page.read_text(encoding="utf-8")
    if type_replacement not in body:
        if body.count(type_anchor) != 1:
            raise SystemExit("ERROR: device list type anchor changed")
        body = 'import{inferDeviceType}from"./higoos-device-type.js";' + body.replace(type_anchor, type_replacement, 1)
        page.write_text(body, encoding="utf-8")

    # Fetch the list and traffic ranking as a single batch so both queries see
    # the same refresh cycle. Keep failures independent for the two panels.
    queries = list(assets.glob("devices.queries-*.js"))
    if len(queries) != 1:
        raise SystemExit("ERROR: expected one device query asset")
    query = queries[0]
    source = query.read_text(encoding="utf-8")
    batch = ('let h5000mBatch,h5000mBatchAt=0;const h5000mFetch=i=>{'
             'const now=Date.now();if(!h5000mBatch||now-h5000mBatchAt>4000){'
             'h5000mBatchAt=now;h5000mBatch=Promise.allSettled([y.getDevices(),y.getTrafficRanking()])}'
             'return h5000mBatch.then(results=>{const r=results[i];if(r.status==="rejected")throw r.reason;return r.value})};')
    if 'const h5000mFetch=i=>' not in source:
        anchor = 'h=5e3,re=(e=!0)=>m({'
        if source.count(anchor) != 1 or source.count('queryFn:()=>y.getDevices()') != 1 or source.count('queryFn:()=>y.getTrafficRanking()') != 1:
            raise SystemExit("ERROR: device refresh anchors changed")
        source = source.replace(anchor, 'h=5e3;'+batch+'const re=(e=!0)=>m({', 1)
        source = source.replace('queryFn:()=>y.getDevices()', 'queryFn:()=>h5000mFetch(0)', 1)
        source = source.replace('queryFn:()=>y.getTrafficRanking()', 'queryFn:()=>h5000mFetch(1)', 1)
        query.write_text(source, encoding="utf-8")

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
    else:
        start = controller_source.index("function action_higoros_device_remarks()")
        end = controller_source.index(handler_anchor, start)
        controller.write_text(controller_source[:start] + handler.rstrip() + "\n" + controller_source[end:], encoding="utf-8")
    files = {
        assets / "higoos-lan-link.js": (sources / "higoos-lan-link.js").read_text(encoding="utf-8"),
        assets / "higoos-device-type.js": (sources / "higoos-device-type.js").read_text(encoding="utf-8"),
        assets / "higoos-device-vendor.js": (sources / "higoos-device-vendor.js").read_text(encoding="utf-8"),
        assets / "higoos-ieee-vendors.json": (sources / "higoos-ieee-vendors.json").read_text(encoding="utf-8"),
        assets / "higoos-device-remarks.js": (sources / "higoos-device-remarks.js").read_text(encoding="utf-8"),
        root / "lib/upgrade/keep.d/higoos-device-remarks": "/etc/higoos-device-remarks/\n",
    }
    for path, contents in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    logo_dir = assets / "device-logos"
    logo_dir.mkdir(exist_ok=True)
    for logo in (sources / "device-logos").glob("*.svg"):
        (logo_dir / logo.name).write_bytes(logo.read_bytes())
    print("PASS: installed independent HigoOS device remarks")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-device-remarks.py ROOTFS_DIR")
    patch(Path(sys.argv[1]))
