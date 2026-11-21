"""Exercise the authenticated Lua controller used by device-management notes."""
from pathlib import Path
import subprocess
import sys
import tempfile


root = Path(sys.argv[1]).resolve(strict=True)
controller = root / "usr/lib/lua/luci/controller/openclash.lua"
source = controller.read_text(encoding="utf-8")
route = 'entry({"admin", "services", "openclash", "device_remarks"}, call("action_higoros_device_remarks"))'
assert source.count(route) == 1
assert source.count("function action_higoros_device_remarks()") == 1
handler = source[source.index("function action_higoros_device_remarks()"):
                 source.index("\nfunction action_backup()", source.index("function action_higoros_device_remarks()"))]

with tempfile.TemporaryDirectory(prefix="h5000m-remarks-") as temporary:
    base = Path(temporary)
    lua = base / "test.lua"
    lua.write_text(r'''
local base = arg[1]
local store = base .. "/store"
local FS = {}
function FS.stat(path)
    local ok = os.execute("test -e " .. string.format("%q", path))
    return (ok == true or ok == 0) and {} or nil
end
function FS.dir(path)
    if not FS.stat(path) then return nil end
    local names = {}
    for name in io.popen("find " .. string.format("%q", path) .. " -mindepth 1 -maxdepth 1 -type f -printf '%f\n'"):lines() do
        names[#names + 1] = name
    end
    local index = 0
    return function() index = index + 1; return names[index] end
end
function FS.readfile(path)
    local file = io.open(path, "rb")
    if not file then return nil end
    local value = file:read("*a")
    file:close()
    return value
end
function FS.mkdir(path)
    local ok = os.execute("mkdir " .. string.format("%q", path))
    return ok == true or ok == 0
end
function FS.writefile(path, value)
    local file = io.open(path, "wb")
    if not file then return false end
    local ok = file:write(value)
    file:close()
    return ok ~= nil
end
function FS.unlink(path) return os.remove(path) end

local context = { authuser = "root", authsession = "fixture-session", authtoken = "fixture-token" }
package.preload["luci.dispatcher"] = function() return { context = context } end
package.preload["nixio.fs"] = function() return FS end
local request
local HTTP = {}
function HTTP.getenv(key) return key == "REQUEST_METHOD" and request.method end
function HTTP.formvalue(key) return request.form[key] end
function HTTP.status(code) request.status = code end
function HTTP.prepare_content() end
function HTTP.write_json(data) request.data = data end
package.preload["luci.http"] = function() return HTTP end
''' + handler.replace('"/etc/higoos-device-remarks"', 'store') + r'''
local function run(method, user, form)
    context.authuser = user
    request = { method = method, form = form or {} }
    action_higoros_device_remarks()
    return request
end

local mac, other, note, token = "020000000001", "020000000002", "客厅手机", "fixture-token"
assert(run("GET", "guest").status == 403)
assert(run("POST", "root", { token = "wrong", mac = mac, note = note }).status == 403)
assert(run("POST", "root", { token = token, mac = "../abc", note = note }).status == 400)
assert(run("POST", "root", { token = token, mac = mac, note = note }).status == 200)
assert(run("POST", "root", { token = token, mac = other, note = "PC" }).status == 200)
local listed = run("GET", "root")
assert(listed.status == 200 and listed.data.remarks[mac] == note and listed.data.remarks[other] == "PC")
assert(run("POST", "root", { token = token, mac = mac, note = "" }).status == 200)
listed = run("GET", "root")
assert(not listed.data.remarks[mac] and listed.data.remarks[other] == "PC")
''', encoding="utf-8")
    subprocess.run(["lua5.1", str(lua), temporary], check=True)

print("PASS: authenticated LuCI device remarks saved, read, and cleared without changing device names")
