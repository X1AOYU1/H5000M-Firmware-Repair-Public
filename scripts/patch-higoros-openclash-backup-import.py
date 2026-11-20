#!/usr/bin/env python3
"""Add a filtered OpenClash backup importer to HigoOS and LuCI."""
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
state_replacement = 've=g("config"),X=g(""),backupFile=g(null),he=W(()=>'
if 'backupFile=g(null),he=W(()=>' in page:
    pass
elif page.count(state_anchor) == 1:
    page = page.replace(state_anchor, state_replacement, 1)
else:
    raise SystemExit("ERROR: OpenClash importer state anchor changed")

method_anchor = 'async function Je(){'
method = (
    'async function uploadBackup(){if(t.value||!backupFile.value)return;const file=backupFile.value;'
    't.value=!0;V.value="正在安全导入备份";try{'
    'const form=new FormData();form.append("backup_file",file,file.name);'
    'const response=await fetch("/cgi-bin/luci/admin/services/openclash/restore_backup",{method:"POST",credentials:"same-origin",body:form});'
    'const text=await response.text();let result;try{result=JSON.parse(text)}catch{throw new Error("备份接口返回无法识别的响应（HTTP "+response.status+")")} '
    'if(!response.ok||result.status!=="success")throw new Error(result.message||"备份导入失败（HTTP "+response.status+")");'
    'backupFile.value=null;await N();V.value=result.message||"备份已导入，OpenClash 保持关闭"'
    '}catch(error){U(error)}finally{t.value=!1}}'
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
)
if '导入 OpenClash 备份 (.tar.gz)' not in page and '导入 OpenClash 备份 (.tar / .tar.gz)' not in page and page.count(toolbar_anchor) == 1:
    page = page.replace(toolbar_anchor, toolbar_replacement, 1)
elif '导入 OpenClash 备份 (.tar.gz)' not in page and '导入 OpenClash 备份 (.tar / .tar.gz)' not in page:
    raise SystemExit("ERROR: OpenClash files toolbar anchor changed")

if '/cgi-bin/luci/admin/services/openclash/restore_backup' not in page or 'backupFile.value' not in page or 'id:"oc-backup-file"' not in page:
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
route_anchor = 'entry({"admin", "services", "openclash", "restore_backup"}, call("action_restore_backup"))'
route_replacement = (
    'local oc_restore_entry = ' + route_anchor + '\n'
    'oc_restore_entry.leaf = true\n'
    'oc_restore_entry.sysauth = false'
)
if route_anchor in controller_source:
    controller_source = controller_source.replace(route_anchor, route_replacement, 1)
elif 'oc_restore_entry.sysauth = false' not in controller_source:
    raise SystemExit("ERROR: OpenClash backup route registration changed")
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
    '\t\t\tlocal cookie = HTTP.getenv("HTTP_COOKIE") or ""\n'
    '\t\t\tlocal lan_ip = SYS.exec("uci -q get network.lan.ipaddr 2>/dev/null") or ""\n'
    '\t\t\tlan_ip = lan_ip:match("([0-9]+%.[0-9]+%.[0-9]+%.[0-9]+)")\n'
    '\t\t\tlocal auth_status\n'
    '\t\t\tif #cookie <= 8192 and cookie:find("higo%-mesh%-view%-") and lan_ip then\n'
    '\t\t\t\tauth_status = SYS.exec("curl --noproxy \'*\' -sS --connect-timeout 2 --max-time 5 -o /dev/null -w \'%{http_code}\' -H " .. UTIL.shellquote("Cookie: " .. cookie) .. " " .. UTIL.shellquote("http://" .. lan_ip .. "/api/v1/auth/me") .. " 2>/dev/null")\n'
    '\t\t\tend\n'
    '\t\t\tif not auth_status or auth_status:match("(%d%d%d)") ~= "200" then\n'
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
