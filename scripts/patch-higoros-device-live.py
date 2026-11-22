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

    network = one("NetworkPage-*.js")
    body = network.read_text(encoding="utf-8")
    body = replace(body, 'o=qs(i.node.type,l.iconColor)',
                   'o=i.node.type==="device"?topologyDeviceIcon(i.node,l.iconColor):qs(i.node.type,l.iconColor)')
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
    controller.write_text(body, encoding="utf-8")
    for name in ("higoos-device-live.js", "higoos-topology-icons.js"):
        (assets / name).write_bytes((sources / name).read_bytes())
    print("PASS: installed live wireless association state and device topology icons")


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
