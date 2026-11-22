#!/usr/bin/env python3
"""Share authoritative wireless state and type-aware topology across the SPA."""
from pathlib import Path
import sys


def patch(root):
    sources = Path(__file__).parent
    assets = root / "usr/share/higoros/web/assets"
    def one(pattern):
        files = list(assets.glob(pattern))
        if len(files) != 1:
            raise SystemExit(f"ERROR: expected one {pattern}, found {len(files)}")
        return files[0]
    def replace(source, old, new):
        if new in source:
            return source
        if source.count(old) != 1:
            raise SystemExit(f"ERROR: device live anchor changed: {old}")
        return source.replace(old, new, 1)

    api = one("devices.api-*.js")
    body = api.read_text(encoding="utf-8")
    body = replace(body, 'getDevices:e=>t.get("/devices",{params:e})',
                   'getDevices:e=>withLiveDevices(()=>t.get("/devices",{params:e}))')
    body = replace(body, 'getDevice:e=>t.get(`/devices/${e}`)',
                   'getDevice:e=>withLiveDevice(()=>t.get(`/devices/${e}`))')
    if 'import{withLiveDevices,' not in body:
        body = 'import{withLiveDevices,withLiveDevice}from"./higoos-device-live.js";' + body
    api.write_text(body, encoding="utf-8")

    # Connection presence must not inherit a five-second traffic refresh setting:
    # two absent samples at that setting cost up to ten seconds before going offline.
    query = one("devices.queries-*.js")
    body = query.read_text(encoding="utf-8")
    body = replace(body,
        'queryFn:()=>h5000mFetch(0),refetchInterval:d(()=>f(e)?h:!1)',
        'queryFn:()=>h5000mFetch(0),refetchInterval:d(()=>f(e)?1e3:!1)')
    query.write_text(body, encoding="utf-8")

    page = one("DevicesPage-*.js")
    body = page.read_text(encoding="utf-8")
    body = replace(body, 'const h5000mDeviceRemark=createDeviceRemark(',
        'const h5000mDeviceHistory=createDeviceHistory({defineComponent:Z,h:Be,ref:M,Modal:N,Button:V});const h5000mDeviceRemark=createDeviceRemark(')
    card = 'r(h5000mDeviceRemark,{mac:t.macAddress,name:t.name},null,8,["mac","name"])'
    body = replace(body, card, card + ',r(h5000mDeviceHistory,{device:t},null,8,["device"])')
    if 'import{createDeviceHistory}' not in body:
        body = 'import{createDeviceHistory}from"./higoos-device-history.js";' + body
    page.write_text(body, encoding="utf-8")

    network = one("NetworkPage-*.js")
    body = network.read_text(encoding="utf-8")
    body = replace(body, 'o=qs(i.node.type,l.iconColor)',
                   'o=i.node.type==="device"?topologyDeviceIcon(i.node,l.iconColor):qs(i.node.type,l.iconColor)')
    body = replace(body, 'name:`${N.name} (${N.devices.length})`,type:N.type,children:N.devices.map(Ce)',
        'name:`${N.devices.some(U=>U.isOnline)?N.name:"离线设备"} (${N.devices.length})`,type:N.type,status:N.devices.some(U=>U.isOnline)?"online":"offline",children:N.devices.map(Ce)')
    if 'import{topologyDeviceIcon}' not in body:
        body = 'import{topologyDeviceIcon}from"./higoos-topology-icons.js";' + body
    network.write_text(body, encoding="utf-8")

    controller = root / "usr/lib/lua/luci/controller/openclash.lua"
    body = controller.read_text(encoding="utf-8")
    route = 'entry({"admin", "services", "openclash", "device_wireless"}, call("action_higoros_device_wireless"))'
    if route not in body:
        anchor = 'entry({"admin", "services", "openclash", "device_remarks"}, call("action_higoros_device_remarks"))'
        body = replace(body, anchor, anchor + '\n\t' + route)
    handler = (sources / "luci-device-wireless.lua").read_text(encoding="utf-8")
    if 'function action_higoros_device_wireless()' not in body:
        body = replace(body, '\nfunction action_backup()', '\n' + handler + '\nfunction action_backup()')
    history_route = 'entry({"admin", "services", "openclash", "device_history"}, call("action_higoros_device_history"))'
    if history_route not in body:
        body = replace(body, route, route + '\n\t' + history_route)
    if 'function action_higoros_device_history()' not in body:
        history_handler = (sources / "luci-device-history.lua").read_text(encoding="utf-8")
        body = replace(body, '\nfunction action_backup()', '\n' + history_handler + '\nfunction action_backup()')
    controller.write_text(body, encoding="utf-8")
    keep = root / "lib/upgrade/keep.d/higoos-device-history"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text('/etc/higoos-forgotten-devices/\n', encoding="utf-8")
    for name in ("higoos-device-live.js", "higoos-device-history.js", "higoos-topology-icons.js"):
        (assets / name).write_bytes((sources / name).read_bytes())
    print("PASS: installed live wireless association state and device topology icons")


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
