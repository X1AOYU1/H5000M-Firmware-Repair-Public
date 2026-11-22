"""Exercise the packed read-only wireless endpoint with realistic ubus fixtures."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
source = (root / "usr/lib/lua/luci/controller/openclash.lua").read_text(encoding="utf-8")
assert source.count('"device_wireless"}, call("action_higoros_device_wireless")') == 1
start = source.index("function action_higoros_device_wireless()")
handler = source[start:source.index("\nfunction action_backup()", start)]
for dependency in ("usr/lib/lua/ubus.so", "usr/lib/lua/uci.so", "usr/lib/rpcd/iwinfo.so"):
    assert (root / dependency).is_file(), f"missing firmware dependency: {dependency}"
subprocess.run(["luac5.1", "-p", str(root / "usr/lib/lua/luci/controller/openclash.lua")], check=True)

with tempfile.TemporaryDirectory() as directory:
    test = Path(directory) / "wireless.lua"
    test.write_text(r'''
local context = {authuser="root", authsession="test"}
local request, fixture, calls
package.preload["luci.dispatcher"] = function() return {context=context} end
package.preload["luci.http"] = function() return {
  prepare_content=function() end, header=function() end,
  getenv=function() return request.method end,
  status=function(code) request.status=code end,
  write_json=function(data) request.data=data end
} end
local mac = "C6:AC:9F:F6:94:22"
local bus = {}
function bus:call(object, method, args)
  calls = calls + 1
  if object == "network.wireless" then return {
    radio0={up=true,interfaces={{ifname="phy0-ap0",config={mode="ap"}}}},
    radio1={up=true,interfaces={{ifname="phy1-ap0",config={mode="ap"}}}}
  } end
  if fixture == "failed" then error("ubus timed out") end
  if object == "hostapd.phy0-ap0" then return {freq=2412,clients={}} end
  if object == "hostapd.phy1-ap0" and fixture ~= "fallback" then
    if fixture == "partial" then return nil end
    return {freq=5180,clients=fixture == "empty" and {} or {[mac]={assoc=true,authorized=true,signal=-45}}}
  end
  if object == "iwinfo" and fixture == "fallback" then
    if method == "info" then return {mode="Master",frequency=5180} end
    return {results={{mac=mac,signal=-49}}}
  end
end
function bus:objects() return {"hostapd.phy0-ap0", "hostapd.phy1-ap0"} end
function bus:close() end
package.preload["ubus"] = function() return {connect=function(path, timeout)
  assert(timeout == 1, "ubus Lua timeout is in seconds")
  return bus
end} end
package.preload["uci"] = function() return {cursor=function() return {
  get=function(self,package,radio,option) return radio == "radio0" and "2g" or "5g" end,
  unload=function() end
} end} end
''' + handler + r'''
local function run(which, user, method)
  calls=0; fixture=which; context.authuser=user or "root"
  request={method=method or "GET",status=200}
  action_higoros_device_wireless()
  return request.data, request.status
end
local function row(data, iface)
  for _, value in ipairs(data.interfaces) do if value.iface == iface then return value end end
end
local data, status = run("online", "guest")
assert(status == 403 and calls == 0, "unauthenticated users cannot inspect associations")
data, status = run("online", "root", "POST")
assert(status == 405 and calls == 0, "endpoint is read-only")
data = run("online")
assert(data.complete == true and #data.interfaces == 2)
assert(row(data,"phy0-ap0").band == "wifi-2.4g")
assert(row(data,"phy1-ap0").band == "wifi-5g")
assert(row(data,"phy1-ap0").clients[1].mac == mac:lower())
assert(row(data,"phy1-ap0").clients[1].signalDbm == -45)
data = run("empty")
assert(data.complete == true and #row(data,"phy1-ap0").clients == 0, "empty association table is valid evidence")
data = run("failed")
assert(data.complete == false and #data.interfaces == 0, "RPC failure is not an empty station table")
data = run("partial")
assert(data.complete == false and #data.interfaces == 1, "partial radio coverage cannot prove offline")
data = run("fallback")
assert(data.complete == true and row(data,"phy1-ap0").clients[1].signalDbm == -49, "iwinfo fallback supports native nl80211 APs")
print("PASS: packed Lua wireless endpoint authentication, two bands, empty/failure distinction and iwinfo fallback")
''', encoding="utf-8")
    subprocess.run(["lua5.1", str(test)], check=True)
