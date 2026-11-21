function action_higoros_device_remarks()
	local DISP = require "luci.dispatcher"
	local LFS = require "nixio.fs"
	local HTTP = require "luci.http"
	local context = DISP.context or {}
	local token = context.authtoken
	local method = HTTP.getenv("REQUEST_METHOD")
	local function reply(code, reason, payload)
		HTTP.status(code, reason)
		HTTP.prepare_content("application/json")
		HTTP.write_json(payload)
	end
	if context.authuser ~= "root" or not context.authsession or not token then
		return reply(403, "Forbidden", { error = "请重新登录后再试" })
	end
	if method ~= "GET" and method ~= "POST" then
		return reply(405, "Method Not Allowed", { error = "请求方法不支持" })
	end
	if method == "POST" and HTTP.formvalue("token") ~= token then
		return reply(403, "Forbidden", { error = "登录已失效，请刷新页面后重试" })
	end
	local store = "/etc/higoos-device-remarks"
	local key = HTTP.formvalue("mac") or ""
	if method == "POST" and not key:match("^[0-9a-f][0-9a-f]+$") or
	   method == "POST" and #key ~= 12 then
		return reply(400, "Bad Request", { error = "设备标识无效" })
	end
	if method == "GET" then
		local remarks = {}
		local avatars = {}
		for name in LFS.dir(store) or function() return nil end do
			if name:match("^[0-9a-f][0-9a-f]+$") and #name == 12 then
				local note = LFS.readfile(store .. "/" .. name)
				if note and #note <= 256 then remarks[name] = note end
			end
			local mac = name:match("^avatar%-([0-9a-f]+)$")
			if mac and #mac == 12 then
				local avatar = LFS.readfile(store .. "/" .. name)
				if avatar and #avatar <= 32 then avatars[mac] = avatar end
			end
		end
		return reply(200, "OK", { remarks = remarks, avatars = avatars, token = token })
	end
	if HTTP.formvalue("kind") == "avatar" then
		local value = HTTP.formvalue("avatar") or ""
		local allowed = { Samsung=true, Huawei=true, Apple=true, Xiaomi=true, OPPO=true, vivo=true, Honor=true, Lenovo=true, ASUS=true, Dell=true, HP=true, Computer=true, Phone=true, Tablet=true, TV=true }
		if value ~= "" and not allowed[value] then return reply(400, "Bad Request", {error="头像选项无效"}) end
		local path = store .. "/avatar-" .. key
		if value == "" then
			if not LFS.unlink(path) and LFS.stat(path) then return reply(500, "Internal Server Error", {error="重置头像失败"}) end
		else
			if not LFS.stat(store) and not LFS.mkdir(store) then return reply(500, "Internal Server Error", {error="无法创建存储目录"}) end
			if not LFS.writefile(path, value) then return reply(500, "Internal Server Error", {error="保存头像失败"}) end
		end
		return reply(200, "OK", {avatar=value})
	end
	local note = HTTP.formvalue("note")
	if type(note) ~= "string" or #note > 256 or note:find("[%z\1-\31\127]") then
		return reply(400, "Bad Request", { error = "备注最多 256 字节且不能包含换行" })
	end
	note = note:match("^%s*(.-)%s*$")
	local path = store .. "/" .. key
	if note == "" then
		if not LFS.unlink(path) and LFS.stat(path) then
			return reply(500, "Internal Server Error", { error = "删除备注失败" })
		end
	else
		if not LFS.stat(store) and not LFS.mkdir(store) then
			return reply(500, "Internal Server Error", { error = "无法创建备注存储目录" })
		end
		local ok = LFS.writefile(path, note)
		if not ok then
			return reply(500, "Internal Server Error", { error = "路由器无法写入备注文件" })
		end
	end
	return reply(200, "OK", { note = note })
end
