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
    't.value=!0;V.value="正在安全导入备份";try{const body=new FormData;body.append("backup_file",file);'
    'const response=await fetch("/cgi-bin/luci/admin/services/openclash/restore_backup",'
    '{method:"POST",credentials:"same-origin",headers:{"X-Requested-With":"XMLHttpRequest"},body});'
    'const result=await response.json();if(!response.ok||result.status!=="success")'
    'throw new Error(result.message||"备份导入失败");backupFile.value=null;V.value="备份已导入，OpenClash 保持关闭";'
    'await N()}catch(error){U(error)}finally{t.value=!1}}'
)
if "async function uploadBackup()" not in page and page.count(method_anchor) == 1:
    page = page.replace(method_anchor, method + method_anchor, 1)
elif "async function uploadBackup()" not in page:
    raise SystemExit("ERROR: OpenClash importer method anchor changed")

toolbar_anchor = 'f.value==="files"?(o(),y("section",Hl,[s("div",Ql,['
toolbar_replacement = (
    'f.value==="files"?(o(),y("section",Hl,[s("div",Ql,['
    's("input",{type:"file",accept:".tar.gz,application/gzip",disabled:t.value,'
    'onChange:e[62]||(e[62]=l=>backupFile.value=l.target.files?.[0]||null),'
    'class:"rounded border border-line-1/70 bg-bg-2/50 p-2"},null,8,["disabled"]),'
    'm(i(p),{variant:"secondary",disabled:t.value||!backupFile.value,onClick:uploadBackup},'
    '{default:r(()=>[...e[63]||(e[63]=[d("导入 OpenClash 备份 (.tar.gz)",-1)])]),_:1},8,["disabled"]),'
)
if '导入 OpenClash 备份 (.tar.gz)' not in page and page.count(toolbar_anchor) == 1:
    page = page.replace(toolbar_anchor, toolbar_replacement, 1)
elif '导入 OpenClash 备份 (.tar.gz)' not in page:
    raise SystemExit("ERROR: OpenClash files toolbar anchor changed")

if '/cgi-bin/luci/admin/services/openclash/restore_backup' not in page or 'backupFile.value' not in page:
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
	local tarok = SYS.call("tar tzf " .. quoted .. " >" .. listfile .. " 2>/dev/null") == 0
	local has_profile, unsafe = false, false
	local allowed, count = {}, 0
	local unsafe_types = SYS.call("tar tvzf " .. quoted .. " 2>/dev/null | grep -qE '^[bcp lhs]'") == 0
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
			if SYS.call("tar -C " .. UTIL.shellquote(stage) .. " -xzf " .. quoted .. " -T " .. UTIL.shellquote(allowfile) .. " >/dev/null 2>&1") == 0 then
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
filename_anchor = "\t\t\ttarget_path = backup_dir .. name"
filename_check = (
    "\t\t\tif not name:match(\"%.tar%.gz$\") then\n"
    "\t\t\t\tstream_err = \"Backup must be a .tar.gz archive\"\n"
    "\t\t\t\treturn\n"
    "\t\t\tend\n\n" + filename_anchor
)
if filename_anchor in handler and "Backup must be a .tar.gz archive" not in handler:
    handler = handler.replace(filename_anchor, filename_check, 1)
elif "Backup must be a .tar.gz archive" not in handler:
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
controller.write_text(controller_source[:handler_start] + handler + controller_source[handler_end:], encoding="utf-8")
print("PASS: HigoOS backup import added; restore filters donor core/cache/geo, pins H5000M Meta settings, and leaves OpenClash disabled")
