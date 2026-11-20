#!/usr/bin/env python3
"""Add authenticated OpenClash backup import and export to HigoOS."""
from pathlib import Path
import sys


root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
pages = sorted(assets.glob("OpenClashPage-*.js"))
lua = root / "usr/lib/lua/luci/openclash.lua"
controller = root / "usr/lib/lua/luci/controller/openclash.lua"
if len(pages) != 1 or not lua.is_file() or not controller.is_file():
    raise SystemExit("ERROR: HigoOS OpenClash frontend or LuCI restore library is missing")

page = pages[0].read_text(encoding="utf-8")
state_anchor = 've=g("config"),X=g(""),he=W(()=>'
state_replacement = state_anchor.replace('he=W', 'backupFile=g(null),backupType=g("backup"),he=W', 1)
if 'backupFile=g(null),backupType=g("backup"),he=W(()=>' in page:
    pass
elif page.count(state_anchor) == 1:
    page = page.replace(state_anchor, state_replacement, 1)
else:
    raise SystemExit("ERROR: OpenClash importer state anchor changed")

method_anchor = 'async function Je(){'
method = (
    'async function backupRequest(params,options={}){const path=params.operation==="download"?"backup":"upload";const response=await fetch("/cgi-bin/luci/higoros/openclash/"+path+"?"+new URLSearchParams(params),{credentials:"same-origin",...options});'
    'if(!response.ok){const message=await response.text();throw new Error(message||"请求失败（HTTP "+response.status+")")}if(params.operation!=="download"){const result=await response.clone().json();if(result.status!=="success")throw new Error(result.message||"备份请求失败")}return response}\n'
    'async function downloadBackup(){if(t.value)return;t.value=!0;V.value="正在生成 OpenClash 备份";try{'
    'const response=await backupRequest({operation:"download",backup_type:backupType.value});'
    'const blob=await response.blob();if(!blob.size)throw new Error("备份文件为空");'
    'const match=(response.headers.get("Content-Disposition")||"").match(/filename="?([^";]+)"?/i);'
    'const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=match?match[1]:"OpenClash-backup.tar.gz";'
    'document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);V.value="备份已生成并下载"'
    '}catch(error){U(error)}finally{t.value=!1}}'
    'async function uploadBackup(){if(t.value||!backupFile.value)return;const file=backupFile.value,id=Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,"0")).join("");'
    't.value=!0;V.value="正在安全导入备份";let started=!1;try{'
    'await backupRequest({operation:"start",upload_id:id,filename:file.name},{method:"POST"});started=!0;'
    'for(let offset=0;offset<file.size;offset+=1048576){V.value="正在上传备份 "+Math.min(100,Math.round((offset+1048576)/file.size*100))+"%";'
    'await backupRequest({operation:"chunk",upload_id:id,filename:file.name,offset:String(offset)},{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file.slice(offset,offset+1048576)})}'
    'const response=await backupRequest({operation:"finish",upload_id:id,filename:file.name},{method:"POST"});const result=await response.json();'
    'if(result.status!=="success")throw new Error(result.message||"备份导入失败");started=!1;backupFile.value=null;await N();V.value=result.message||"备份已导入，OpenClash 保持关闭"'
    '}catch(error){if(started)try{await backupRequest({operation:"cancel",upload_id:id,filename:file.name},{method:"POST"})}catch{}U(error)}finally{t.value=!1}}'
)
if "async function uploadBackup()" not in page and page.count(method_anchor) == 1:
    page = page.replace(method_anchor, method + method_anchor, 1)
elif "async function uploadBackup()" not in page:
    raise SystemExit("ERROR: OpenClash importer method anchor changed")

toolbar_anchor = 'f.value==="files"?(o(),y("section",Hl,[s("div",Ql,['
toolbar_replacement = (
    'f.value==="files"?(o(),y("section",Hl,[s("div",Ql,['
    's("input",{id:"oc-backup-file",type:"file",accept:".tar,.tar.gz,application/x-tar,application/gzip",style:{display:"none"},'
    'onChange:e[62]||(e[62]=l=>backupFile.value=l.target.files?.[0]||null),'
    'class:"rounded border border-line-1/70 bg-bg-2/50 p-2"},null,8,["onChange"]),'
    'm(i(p),{variant:"secondary",disabled:t.value,onClick:()=>document.getElementById("oc-backup-file")?.click()},'
    '{default:r(()=>[d(backupFile.value?.name||"选择备份文件",-1)]),_:1},8,["disabled"]),'
    'm(i(p),{variant:"secondary",disabled:t.value||!backupFile.value,onClick:uploadBackup},'
    '{default:r(()=>[...e[63]||(e[63]=[d("导入 OpenClash 备份 (.tar / .tar.gz)",-1)])]),_:1},8,["disabled"]),'
    's("select",{value:backupType.value,disabled:t.value,"aria-label":"备份范围",class:"rounded border border-line-1/70 bg-bg-2/50 p-2",onChange:e=>backupType.value=e.target.value},['
    's("option",{value:"backup"},"完整备份"),s("option",{value:"backup_ex_core"},"备份，不含内核"),'
    's("option",{value:"backup_only_config"},"仅配置"),s("option",{value:"backup_only_rule"},"仅规则提供者"),'
    's("option",{value:"backup_only_proxy"},"仅代理提供者"),s("option",{value:"backup_only_core"},"仅内核")]),'
    'm(i(p),{variant:"secondary",disabled:t.value,onClick:downloadBackup},{default:r(()=>[...e[64]||(e[64]=[d("生成备份")])]),_:1},8,["disabled"]),'
)
if '导入 OpenClash 备份 (.tar.gz)' not in page and '导入 OpenClash 备份 (.tar / .tar.gz)' not in page and page.count(toolbar_anchor) == 1:
    page = page.replace(toolbar_anchor, toolbar_replacement, 1)
elif '导入 OpenClash 备份 (.tar.gz)' not in page and '导入 OpenClash 备份 (.tar / .tar.gz)' not in page:
    raise SystemExit("ERROR: OpenClash files toolbar anchor changed")

if 'higoros/openclash/' not in page or 'application/octet-stream' not in page or 'backupFile.value' not in page or 'id:"oc-backup-file"' not in page:
    raise SystemExit("ERROR: HigoOS backup importer was not installed")
pages[0].write_text(page, encoding="utf-8")

source = lua.read_text(encoding="utf-8")
start = source.find("function restore_backup(archive)")
end = source.find("\nfunction get_age_keys", start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: filtered OpenClash backup restore anchor changed")
replacement = r'''function restore_backup(archive)
	local quoted = UTIL.shellquote(archive)
	local listfile = "/tmp/oc_restore.list"
	local allowfile = "/tmp/oc_restore.allow"
	local stage = "/tmp/oc_restore_stage"
	local restored = false
	local gzip_archive = archive:match("%.tar%.gz$") ~= nil
	local tar_list_options = gzip_archive and "tzf " or "tf "
	local tar_verbose_options = gzip_archive and "tvzf " or "tvf "
	local tar_extract_options = gzip_archive and "-xzf " or "-xf "
	local tarok = SYS.call("tar " .. tar_list_options .. quoted .. " >" .. listfile .. " 2>/dev/null") == 0
	local has_profile, unsafe = false, false
	local allowed, count = {}, 0
	local unsafe_types = SYS.call("tar " .. tar_verbose_options .. quoted .. " 2>/dev/null | grep -qE '^[bcp lhs]'") == 0
	if tarok and not unsafe_types then
		for line in io.lines(listfile) do
			line = line:gsub("/$", "")
			if line:match("^/") or line:match("^%.%./") or line:find("/../", 1, true) or line:sub(-3) == "/.." then unsafe = true end
			local category, name = line:match("^%./([%w_%-]+)/([^/]+)$")
			if name and not name:match("^[%w_.%-]+$") then unsafe = true end
			local ok = line == "./openclash"
				or (category == "config" and name and name:match("%.ya?ml$"))
				or ((category == "custom" or category == "overwrite" or category == "proxy_provider" or category == "rule_provider") and name ~= nil)
				or line == "./china_ip_route.ipset"
				or line == "./china_ip6_route.ipset"
			if ok then
				count = count + 1
				if count > 2048 then unsafe = true; break end
				allowed[#allowed + 1] = line
				if line:match("^%./config/[%w_.%-]+%.ya?ml$") then has_profile = true end
			end
		end
	end
	if tarok and not unsafe_types and has_profile and not unsafe then
		local allow = io.open(allowfile, "w")
		if allow then
			for _, path in ipairs(allowed) do allow:write(path, "\n") end
			allow:close()
			SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " && mkdir -p " .. UTIL.shellquote(stage))
			if SYS.call("tar -C " .. UTIL.shellquote(stage) .. " " .. tar_extract_options .. quoted .. " -T " .. UTIL.shellquote(allowfile) .. " >/dev/null 2>&1") == 0 then
				local config_dir = stage .. "/config"
				local selected
				local staged_uci = stage .. "/openclash"
				if SYS.call("test -f " .. UTIL.shellquote(staged_uci)) == 0 then
					local in_main = false
					for line in io.lines(staged_uci) do
						if line:match("^%s*config%s+") then
							in_main = line:match("^%s*config%s+openclash%s+['\"]config['\"]") ~= nil
						elseif in_main then
							local key, value = line:match("^%s*option%s+([%w_]+)%s+['\"]([^'\"]*)['\"]")
							if key == "config_path" then selected = value:match("([^/]+)$"); break end
						end
					end
				end
				if not selected or not selected:match("^[%w_.%-]+%.ya?ml$") or SYS.call("test -f " .. UTIL.shellquote(config_dir .. "/" .. selected)) ~= 0 then
					selected = SYS.exec("find " .. UTIL.shellquote(config_dir) .. " -maxdepth 1 -type f -name '*.yaml' -print -quit")
					selected = selected and selected:match("([^/]+)\n?$")
				end
				if selected and selected:match("^[%w_.%-]+%.ya?ml$") then
					local ok = SYS.call("mkdir -p /etc/openclash/config /etc/openclash/custom /etc/openclash/overwrite /etc/openclash/proxy_provider /etc/openclash/rule_provider") == 0
					SYS.call("uci set openclash.config.enable=0 && uci commit openclash && /etc/init.d/openclash stop >/dev/null 2>&1")
					for _, name in ipairs({"config", "custom", "overwrite", "proxy_provider", "rule_provider"}) do
						local src = stage .. "/" .. name
						local dest = "/etc/openclash/" .. name
						if SYS.call("test -d " .. UTIL.shellquote(src)) == 0 and SYS.call("find " .. UTIL.shellquote(src) .. " -type f -print -quit | grep -q .") == 0 then
							ok = ok and SYS.call("cp -f " .. UTIL.shellquote(src) .. "/* " .. UTIL.shellquote(dest .. "/")) == 0
						end
					end
					for _, name in ipairs({"china_ip_route.ipset", "china_ip6_route.ipset"}) do
						local src = stage .. "/" .. name
						if SYS.call("test -f " .. UTIL.shellquote(src)) == 0 then
							ok = ok and SYS.call("cp -f " .. UTIL.shellquote(src) .. " /etc/openclash/") == 0
						end
					end
					local staged_uci = stage .. "/openclash"
					if SYS.call("test -f " .. UTIL.shellquote(staged_uci) .. " && grep -qE \"^config[[:space:]]+openclash[[:space:]]+['\\\"]config['\\\"]\" " .. UTIL.shellquote(staged_uci)) == 0 then
						ok = ok and SYS.call("cp -f " .. UTIL.shellquote(staged_uci) .. " /etc/config/openclash") == 0
					end
					ok = ok and SYS.call("uci set openclash.config.config_path=" .. UTIL.shellquote("/etc/openclash/config/" .. selected)) == 0
					ok = ok and SYS.call("uci set openclash.config.enable=0 && uci set openclash.config.core_type=Meta && uci set openclash.config.interface_name=br-lan && uci set openclash.config.lan_interface_name=br-lan && uci set openclash.config.en_mode=fake-ip-tun && uci set openclash.config.smart_enable=0 && uci set openclash.config.auto_smart_switch=0 && uci set openclash.config.smart_enable_lgbm=0 && uci -q delete openclash.config.stack_type && uci commit openclash") == 0
					restored = ok
				end
			end
		end
	end
	SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " " .. UTIL.shellquote(listfile) .. " " .. UTIL.shellquote(allowfile))
	return restored
end
'''
lua.write_text(source[:start] + replacement + source[end:], encoding="utf-8")

controller_source = controller.read_text(encoding="utf-8")
session_anchor = 'local fs = require "luci.openclash"\n'
session_helper = r'''local function higoros_session_valid()
	local cookie = HTTP.getenv("HTTP_COOKIE") or ""
	local lan_ip = SYS.exec("uci -q get network.lan.ipaddr 2>/dev/null") or ""
	lan_ip = lan_ip:match("([0-9]+%.[0-9]+%.[0-9]+%.[0-9]+)")
	if #cookie > 8192 or not cookie:find("higo%-mesh%-view%-") or not lan_ip then return false end
	local status = SYS.exec("curl --noproxy '*' -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}' -H " .. UTIL.shellquote("Cookie: " .. cookie) .. " " .. UTIL.shellquote("http://" .. lan_ip .. "/api/v1/auth/me") .. " 2>/dev/null")
	return status and status:match("(%d%d%d)") == "200"
end
'''
if session_anchor in controller_source and "local function higoros_session_valid()" not in controller_source:
    controller_source = controller_source.replace(session_anchor, session_anchor + session_helper, 1)
elif "local function higoros_session_valid()" not in controller_source:
    raise SystemExit("ERROR: OpenClash HigoOS session validation anchor changed")
backup_route_anchor = 'entry({"admin", "services", "openclash", "backup"}, call("action_backup"))'
backup_route = 'entry({"higoros", "openclash", "backup"}, call("action_higoros_backup"))'
backup_route_auth = (
    'local higoros_backup_entry = ' + backup_route + '\n'
    'higoros_backup_entry.leaf = true\n'
    'higoros_backup_entry.sysauth = false'
)
if 'higoros_backup_entry.sysauth = false' not in controller_source:
    if controller_source.count(backup_route_anchor) == 1:
        controller_source = controller_source.replace(backup_route_anchor, backup_route + "\n\t" + backup_route_anchor, 1)
    if backup_route not in controller_source:
        raise SystemExit("ERROR: OpenClash backup route anchor changed")
    controller_source = controller_source.replace(backup_route, backup_route_auth, 1)
backup_action_anchor = "\nfunction action_backup()"
backup_action = r'''
function action_higoros_backup()
	if not higoros_session_valid() then
		HTTP.prepare_content("application/json")
		HTTP.write_json({ status = "error", message = "HigoOS session is invalid or expired; sign in again" })
		return
	end
    local actions = {
		backup = action_backup,
		backup_ex_core = action_backup_ex_core,
		backup_only_config = action_backup_only_config,
		backup_only_rule = action_backup_only_rule,
		backup_only_proxy = action_backup_only_proxy,
		backup_only_core = action_backup_only_core
	}
	local action = actions[HTTP.formvalue("backup_type") or ""]
	if not action then
		HTTP.prepare_content("application/json")
		HTTP.write_json({ status = "error", message = "Unsupported backup type" })
		return
	end
	return action()
end
'''
if backup_action_anchor in controller_source and "function action_higoros_backup()" not in controller_source:
    controller_source = controller_source.replace(backup_action_anchor, "\n" + backup_action + backup_action_anchor, 1)
elif "function action_higoros_backup()" not in controller_source:
    raise SystemExit("ERROR: OpenClash backup action insertion anchor changed")

upload_action = r'''
function action_higoros_upload()
	local function respond(status, message)
		HTTP.prepare_content("application/json")
		HTTP.write_json({ status = status, message = message })
	end
	if not higoros_session_valid() then return respond("error", "HigoOS session is invalid or expired; sign in again") end
	local operation = HTTP.formvalue("operation") or ""
	local id = HTTP.formvalue("upload_id") or ""
	local filename = (HTTP.formvalue("filename") or ""):lower()
	if not id:match("^[a-f0-9]+$") or #id ~= 32 then return respond("error", "Invalid upload id") end
	local suffix = filename:match("%.tar%.gz$") and ".tar.gz" or (filename:match("%.tar$") and ".tar" or nil)
	if not suffix then return respond("error", "Backup must be a .tar or .tar.gz archive") end
	local path = "/tmp/higoos_openclash_" .. id .. suffix
	if operation == "start" then
		local fp = io.open(path, "wb")
		if not fp then return respond("error", "Unable to create temporary backup file") end
		fp:close()
		return respond("success", "Upload started")
	elseif operation == "chunk" then
		local chunk = HTTP.content() or ""
		local offset = tonumber(HTTP.formvalue("offset") or "")
		if #chunk == 0 or #chunk > 1048576 or not offset or offset < 0 then return respond("error", "Invalid backup upload chunk") end
		local fp = io.open(path, "r+b")
		if not fp then return respond("error", "Backup upload has expired; start again") end
		local current = fp:seek("end") or 0
		if current ~= offset or current + #chunk > 134217728 then fp:close(); return respond("error", "Backup upload offset or size is invalid") end
		fp:write(chunk)
		fp:close()
		return respond("success", "Chunk received")
	elseif operation == "cancel" then
		fs.unlink(path)
		return respond("success", "Upload cancelled")
	elseif operation == "finish" then
		local fp = io.open(path, "rb")
		if not fp then return respond("error", "Backup upload file is missing") end
		local size = fp:seek("end") or 0
		fp:close()
		if size == 0 then fs.unlink(path); return respond("error", "Backup file is empty") end
		local ok, restored = pcall(fs.restore_backup, path)
		fs.unlink(path)
		if not ok then return respond("error", "Backup restore error: " .. tostring(restored):sub(1, 512)) end
		if not restored then return respond("error", "Backup File Restore Failed") end
		return respond("success", "Backup imported; OpenClash remains disabled")
	end
	return respond("error", "Unsupported upload operation")
end
'''
upload_action_anchor = "\nfunction action_backup()"
if "function action_higoros_upload()" not in controller_source and controller_source.count(upload_action_anchor) == 1:
    controller_source = controller_source.replace(upload_action_anchor, "\n" + upload_action + upload_action_anchor, 1)
elif "function action_higoros_upload()" not in controller_source:
    raise SystemExit("ERROR: OpenClash upload action insertion anchor changed")

upload_route = 'entry({"higoros", "openclash", "upload"}, call("action_higoros_upload"))'
upload_route_auth = (
    'local higoros_upload_entry = ' + upload_route + '\n'
    'higoros_upload_entry.leaf = true\n'
    'higoros_upload_entry.sysauth = false'
)
if 'higoros_upload_entry.sysauth = false' not in controller_source:
    if controller_source.count(backup_route_anchor) == 1:
        controller_source = controller_source.replace(backup_route_anchor, backup_route_anchor + "\n\t" + upload_route, 1)
    if upload_route not in controller_source:
        raise SystemExit("ERROR: OpenClash upload route anchor changed")
    controller_source = controller_source.replace(upload_route, upload_route_auth, 1)
route_anchor = 'entry({"admin", "services", "openclash", "restore_backup"}, call("action_restore_backup"))'
route_replacement = (
    'local oc_restore_entry = ' + route_anchor + '\n'
    'oc_restore_entry.leaf = true\n'
    'oc_restore_entry.sysauth = false'
)
if 'oc_restore_entry.sysauth = false' not in controller_source:
    if route_anchor not in controller_source:
        raise SystemExit("ERROR: OpenClash backup route registration changed")
    controller_source = controller_source.replace(route_anchor, route_replacement, 1)
handler_start = controller_source.find("function action_restore_backup()")
handler_end = controller_source.find("\nfunction action_config_file_read", handler_start)
if handler_start < 0 or handler_end < 0:
    raise SystemExit("ERROR: OpenClash backup upload endpoint changed")
handler = controller_source[handler_start:handler_end]
state = "local started, fp, target_path, stream_err = false, nil, nil, nil"
if state in handler:
    handler = handler.replace(state, "local started, fp, target_path, stream_err, file_size = false, nil, nil, nil, 0", 1)
elif "local started, fp, target_path, stream_err, file_size" not in handler:
    raise SystemExit("ERROR: OpenClash backup upload state changed")
auth_anchor = '\t\t\tstarted = true\n\n\t\t\tlocal name = (meta and meta.file) or ""'
auth_check = (
    '\t\t\tstarted = true\n\n'
    '\t\t\tif not higoros_session_valid() then\n'
    '\t\t\t\tstream_err = "HigoOS session is invalid or expired; sign in again"\n'
    '\t\t\t\treturn\n'
    '\t\t\tend\n\n'
    '\t\t\tlocal name = (meta and meta.file) or ""'
)
if auth_anchor in handler:
    handler = handler.replace(auth_anchor, auth_check, 1)
elif 'HigoOS session is invalid or expired' not in handler:
    raise SystemExit("ERROR: OpenClash upload authorization anchor changed")
filename_anchor = "\t\t\ttarget_path = backup_dir .. name"
filename_check = (
    "\t\t\tif not name:match(\"%.tar%.gz$\") and not name:match(\"%.tar$\") then\n"
    "\t\t\t\tstream_err = \"Backup must be a .tar or .tar.gz archive\"\n"
    "\t\t\t\treturn\n"
    "\t\t\tend\n\n" + filename_anchor
)
if filename_anchor in handler and "Backup must be a .tar or .tar.gz archive" not in handler:
    handler = handler.replace(filename_anchor, filename_check, 1)
elif "Backup must be a .tar or .tar.gz archive" not in handler:
    raise SystemExit("ERROR: OpenClash backup filename validation anchor changed")
chunk_write = "\t\tif chunk and fp then\n\t\t\tfp:write(chunk)\n\t\tend"
chunk_limited = (
    "\t\tif chunk and fp then\n"
    "\t\t\tfile_size = file_size + #chunk\n"
    "\t\t\tif file_size > 134217728 then stream_err = \"Backup archive exceeds 128 MiB limit\"; return end\n"
    "\t\t\tfp:write(chunk)\n\t\tend"
)
if chunk_write in handler:
    handler = handler.replace(chunk_write, chunk_limited, 1)
elif "Backup archive exceeds 128 MiB limit" not in handler:
    raise SystemExit("ERROR: OpenClash backup upload stream changed")
handler = handler.replace(
    "\tif stream_err then\n\t\tif target_path then",
    "\tif stream_err then\n\t\tif fp then fp:close(); fp = nil end\n\t\tif target_path then",
    1,
)
restore_call = "\tlocal restored = fs.restore_backup(target_path)\n\tfs.unlink(target_path)"
restore_call_safe = (
    "\tlocal restore_ok, restored = pcall(fs.restore_backup, target_path)\n"
    "\tfs.unlink(target_path)"
)
if restore_call in handler:
    handler = handler.replace(restore_call, restore_call_safe, 1)
elif "local restore_ok, restored = pcall(fs.restore_backup, target_path)" not in handler:
    raise SystemExit("ERROR: OpenClash restore call changed")
success_branch = "\tif restored then\n\t\tHTTP.write_json({"
safe_branch = (
    "\tif not restore_ok then\n"
    "\t\tHTTP.write_json({ status = \"error\", message = \"Backup restore error: \" .. tostring(restored):sub(1, 512) })\n"
    "\telseif restored then\n\t\tHTTP.write_json({"
)
if success_branch in handler:
    handler = handler.replace(success_branch, safe_branch, 1)
elif 'message = "Backup restore error: " .. tostring(restored):sub(1, 512)' not in handler:
    raise SystemExit("ERROR: OpenClash restore response branch changed")
controller.write_text(controller_source[:handler_start] + handler + controller_source[handler_end:], encoding="utf-8")
print("PASS: HigoOS backup import added; restore filters donor core/cache/geo, pins H5000M Meta settings, and leaves OpenClash disabled")
