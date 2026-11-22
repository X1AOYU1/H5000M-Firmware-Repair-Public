function action_higoros_device_history()
	local HTTP = require "luci.http"
	local FS = require "nixio.fs"
	local context = require("luci.dispatcher").context or {}
	local function reply(code, payload)
		HTTP.status(code)
		HTTP.prepare_content("application/json")
		HTTP.header("Cache-Control", "no-store")
		return HTTP.write_json(payload)
	end
	if context.authuser ~= "root" or not context.authsession or not context.authtoken then
		return reply(403, {error="请重新登录后再试"})
	end
	local method = HTTP.getenv("REQUEST_METHOD")
	if method ~= "GET" and method ~= "POST" then return reply(405, {error="请求方法不支持"}) end
	local store = "/etc/higoos-forgotten-devices"
	local function valid(key) return type(key) == "string" and #key == 12 and key:match("^[0-9a-f]+$") end
	if method == "GET" then
		local markers = {}
		for key in (FS.dir(store) or function() end) do
			if valid(key) then markers[key] = FS.readfile(store .. "/" .. key) end
		end
		return reply(200, {markers=markers, token=context.authtoken})
	end
	if HTTP.formvalue("token") ~= context.authtoken then return reply(403, {error="登录已失效，请刷新后重试"}) end
	local key, action = HTTP.formvalue("mac"), HTTP.formvalue("action")
	if not valid(key) or (action ~= "forget" and action ~= "restore") then
		return reply(400, {error="设备地址或操作无效"})
	end
	local path = store .. "/" .. key
	if action == "restore" then
		local current = FS.readfile(path)
		if current and current ~= HTTP.formvalue("generation") then return reply(409, {error="记录已变化，请刷新后重试"}) end
		if current and not FS.unlink(path) then return reply(500, {error="无法恢复设备记录"}) end
		return reply(200, {ok=true})
	end
	-- Logical deletion is separate from higorosd's periodically rewritten state.
	-- It never changes DHCP, firewall, policy, or native traffic accounting.
	if not FS.mkdirr(store) and not FS.stat(store, "type") then return reply(500, {error="无法创建记录目录"}) end
	FS.chmod(store, 448)
	local generation = (FS.readfile("/proc/sys/kernel/random/uuid") or ""):match("^([%x%-]+)")
	if not generation then return reply(500, {error="无法生成记录标识"}) end
	local temporary = path .. "." .. generation
	if not FS.writefile(temporary, generation) then return reply(500, {error="无法保存清理记录"}) end
	FS.chmod(temporary, 384)
	if not FS.rename(temporary, path) then FS.unlink(temporary); return reply(500, {error="无法保存清理记录"}) end
	return reply(200, {ok=true, generation=generation})
end
