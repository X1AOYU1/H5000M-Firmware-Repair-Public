#!/usr/bin/env python3
"""Add authenticated OpenClash backup import and export to HigoOS."""
from pathlib import Path
import re
import sys


root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
pages = sorted(assets.glob("OpenClashPage-*.js"))
lua = root / "usr/lib/lua/luci/openclash.lua"
controller = root / "usr/lib/lua/luci/controller/openclash.lua"
if len(pages) != 1 or not lua.is_file() or not controller.is_file():
    raise SystemExit("ERROR: HigoOS OpenClash frontend or LuCI restore library is missing")


def matching_delimiter(text, opening):
    pairs = {"[": "]", "(": ")", "{": "}"}
    if text[opening] not in pairs:
        raise ValueError("opening delimiter expected")
    stack = [pairs[text[opening]]]
    quote = None
    escaped = False
    index = opening + 1
    while index < len(text):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            end = text.find("\n", index + 2)
            index = len(text) if end < 0 else end
        elif char == "/" and index + 1 < len(text) and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated comment")
            index = end + 1
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or char != stack.pop():
                raise ValueError("mismatched delimiter")
            if not stack:
                return index
        index += 1
    raise ValueError("unterminated delimiter")

page = pages[0].read_text(encoding="utf-8")
state_anchor = 've=g("config"),X=g(""),he=W(()=>'
state_replacement = state_anchor.replace('he=W', 'backupFile=g(null),uploadType=g("config"),he=W', 1)
if 'backupFile=g(null),uploadType=g("config"),he=W(()=>' in page:
    pass
elif page.count(state_anchor) == 1:
    page = page.replace(state_anchor, state_replacement, 1)
else:
    raise SystemExit("ERROR: OpenClash importer state anchor changed")

method_anchor = 'async function Je(){'
method = (
    'async function backupRequest(params,options={}){const path=params.operation==="download"?"backup":"upload";const response=await fetch("/cgi-bin/luci/higoros/openclash/"+path+"?"+new URLSearchParams(params),{credentials:"same-origin",...options});'
    'if(!response.ok){const raw=await response.text();if(/POST data exceeds maximum allowed length/i.test(raw))throw new Error("路由器拒绝了上传数据块（HTTP "+response.status+"），请重新刷入新版固件");const clean=raw.replace(/<!--[\\s\\S]*?-->/g," ").replace(/<style[^]*?[/]style>/gi," ").replace(/<script[^]*?[/]script>/gi," ").replace(/<[^>]*>/g," ").replace(/\\s+/g," ").trim().slice(0,180);throw new Error(clean||"请求失败（HTTP "+response.status+")")}if(params.operation!=="download"){const result=await response.clone().json();if(result.status!=="success")throw new Error(result.message||"备份请求失败")}return response}\n'
    'async function downloadBackup(){if(t.value)return;t.value=!0;V.value="正在生成 OpenClash 备份";try{'
    'const response=await backupRequest({operation:"download",backup_type:"backup"});'
    'const blob=await response.blob();if(!blob.size)throw new Error("备份文件为空");'
    'const match=(response.headers.get("Content-Disposition")||"").match(/filename="?([^";]+)"?/i);'
    'const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=match?match[1]:"OpenClash-backup.tar.gz";'
    'document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);V.value="备份已生成并下载"'
    '}catch(error){U(error)}finally{t.value=!1}}'
    'async function uploadBackup(){if(t.value||!backupFile.value)return;const file=backupFile.value,archiveType=uploadType.value==="backup-file"||uploadType.value==="clash_meta",valid=uploadType.value==="backup-file"? /\\.tar(?:\\.gz)?$/i.test(file.name):uploadType.value==="clash_meta"?file.name.toLowerCase().endsWith(".tar.gz"): /\\.ya?ml$/i.test(file.name);if(!valid){U(new Error(archiveType?"所选文件后缀与上传类型不匹配":"此类型需要 .yaml 或 .yml 文件"));return}const id=Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,"0")).join("");'
    't.value=!0;V.value="正在安全导入备份";let started=!1;try{'
    'await backupRequest({operation:"start",upload_id:id,filename:file.name,upload_type:uploadType.value},{method:"POST"});started=!0;'
    'for(let offset=0;offset<file.size;offset+=65536){V.value="正在上传备份 "+Math.min(100,Math.round((offset+65536)/file.size*100))+"%";'
    'await backupRequest({operation:"chunk",upload_id:id,filename:file.name,upload_type:uploadType.value,offset:String(offset)},{method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file.slice(offset,offset+65536)})}'
    'const response=await backupRequest({operation:"finish",upload_id:id,filename:file.name,upload_type:uploadType.value},{method:"POST"});const result=await response.json();'
    'if(result.status!=="success")throw new Error(result.message||"备份导入失败");started=!1;backupFile.value=null;await N();V.value=result.message||"备份已导入，OpenClash 保持关闭"'
    '}catch(error){if(started)try{await backupRequest({operation:"cancel",upload_id:id,filename:file.name,upload_type:uploadType.value},{method:"POST"})}catch{}U(error)}finally{t.value=!1}}'
)
if "async function uploadBackup()" not in page and page.count(method_anchor) == 1:
    page = page.replace(method_anchor, method + method_anchor, 1)
elif "async function uploadBackup()" not in page:
    raise SystemExit("ERROR: OpenClash importer method anchor changed")

toolbar_anchor = 'f.value==="files"?(o(),y("section",Hl,[s("div",Ql,['
toolbar_controls = (
    's("label",{for:"oc-backup-file-type",title:"操作类型：",class:"shrink-0 whitespace-nowrap text-muted",style:{fontSize:"14px"}},"上传文件类型："),'
    's("select",{id:"oc-backup-file-type",value:uploadType.value,disabled:t.value,"aria-label":"上传文件类型",class:"w-52 h-9 shrink-0 rounded border border-line-1/70 bg-bg-2/50 px-2 text-sm",onChange:l=>{uploadType.value=l.target.value;backupFile.value=null;const input=document.getElementById("oc-backup-file");if(input)input.value=""}},['
    's("option",{value:"config"},"配置文件 (.yaml)"),s("option",{value:"proxy-provider"},"代理文件"),s("option",{value:"rule-provider"},"规则集文件"),'
    's("option",{value:"clash_meta"},"[Meta] 内核文件 (.tar.gz)"),s("option",{value:"backup-file"},"备份文件 (.tar.gz)"),s("option",{value:"create-file"},"新建文件")],8,["value","disabled"]),'
    's("input",{id:"oc-backup-file",type:"file",accept:uploadType.value==="config"||uploadType.value==="proxy-provider"||uploadType.value==="rule-provider"?".yaml,.yml":uploadType.value==="backup-file"?".tar,.tar.gz,application/x-tar,application/gzip":".tar.gz,application/gzip",style:{display:"none"},'
    'onChange:e[62]||(e[62]=l=>backupFile.value=l.target.files?.[0]||null),'
    'class:"rounded border border-line-1/70 bg-bg-2/50 p-2"},null,8,["accept","onChange"]),'
    'm(i(p),{variant:"primary",class:"!h-9 !min-h-0 shrink-0 whitespace-nowrap !px-3 !py-1 text-sm",style:{margin:0,backgroundColor:"#477fe0",borderColor:"#477fe0",color:"#fff",display:uploadType.value==="create-file"?"none":""},disabled:t.value,onClick:()=>document.getElementById("oc-backup-file")?.click()},'
    '{default:r(()=>[d("选择文件",-1)]),_:1},8,["disabled","style"]),'
    's("span",{class:"w-44 h-9 shrink-0 truncate rounded border border-line-1/70 bg-bg-2/50 px-2 py-1 text-sm text-muted",style:{lineHeight:"26px",display:uploadType.value==="create-file"?"none":""}},backupFile.value?.name||"未选择文件",5),'
    'm(i(p),{variant:"secondary",class:"!h-9 !min-h-0 shrink-0 whitespace-nowrap !px-3 !py-1 text-sm",style:{margin:0,display:uploadType.value==="create-file"?"none":""},disabled:t.value||!backupFile.value,onClick:uploadBackup},'
    '{default:r(()=>[d("上传",-1)]),_:1},8,["disabled","style"]),'
    'm(i(p),{variant:"secondary",class:"!h-9 !min-h-0 shrink-0 whitespace-nowrap !px-3 !py-1 text-sm",style:{margin:0},disabled:t.value,onClick:downloadBackup},{default:r(()=>[d("备份")]),_:1},8,["disabled"]),'
    's("label",{for:"oc-new-file-type",class:"shrink-0 whitespace-nowrap text-muted",style:{fontSize:"14px",display:uploadType.value==="create-file"?"":"none"}},"文件类型：",4),'
    'ie(s("select",{id:"oc-new-file-type","onUpdate:modelValue":l=>ve.value=l,"aria-label":"新建文件类型",class:"h-9 w-36 shrink-0 rounded border border-line-1/70 bg-bg-2/50 px-2 text-sm",style:{display:uploadType.value==="create-file"?"":"none"}},[s("option",{value:"config"},"主配置"),s("option",{value:"overwrite"},"覆写文件"),s("option",{value:"proxy-provider"},"代理提供者"),s("option",{value:"rule-provider"},"规则提供者"),s("option",{value:"custom"},"自定义文件")],4),[[sl,ve.value]]),'
    'ie(s("input",{"onUpdate:modelValue":l=>X.value=l,placeholder:"文件名.yaml",class:"h-9 w-40 shrink-0 rounded border border-line-1/70 bg-bg-2/50 px-2 text-sm",style:{display:uploadType.value==="create-file"?"":"none"}},null,4),[[ye,X.value]]),'
    'm(i(p),{variant:"secondary",class:"!h-9 !min-h-0 shrink-0 whitespace-nowrap !px-3 !py-1 text-sm",style:{margin:0,display:uploadType.value==="create-file"?"":"none"},disabled:t.value||!X.value.trim(),onClick:Je},{default:r(()=>[d("新建文件")]),_:1},8,["disabled","style"])'
)
if page.count(toolbar_anchor) != 1:
    raise SystemExit("ERROR: OpenClash files toolbar anchor changed")
toolbar_start = page.index(toolbar_anchor) + len(toolbar_anchor)
toolbar_end = matching_delimiter(page, toolbar_start - 1)
old_toolbar = page[toolbar_start:toolbar_end]
if "onClick:Je" not in old_toolbar:
    raise SystemExit("ERROR: OpenClash create-file action anchor changed")
# Replace the child list as a unit; a missing child crashes Vue's optimized renderer.
restore_start = old_toolbar.find("oe.value?(o(),")
if restore_start >= 0:
    toolbar_controls += "," + old_toolbar[restore_start:]
elif '"仅恢复文件"' in old_toolbar:
    raise SystemExit("ERROR: OpenClash restore-only action anchor changed")
page = page[:toolbar_start] + toolbar_controls + page[toolbar_end:]

if 'higoros/openclash/' not in page or 'application/octet-stream' not in page or 'backupFile.value' not in page or 'id:"oc-backup-file"' not in page or '上传文件类型' not in page or '未选择文件' not in page:
    raise SystemExit("ERROR: HigoOS backup importer was not installed: " + ", ".join(marker for marker in ('higoros/openclash/', 'application/octet-stream', 'backupFile.value', 'id:\"oc-backup-file\"', '上传文件类型', '未选择文件') if marker not in page))
compact_row_anchor = 'Ql={class:"flex flex-wrap gap-3"}'
compact_row = 'Ql={class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto"}'
if compact_row_anchor in page:
    page = page.replace(compact_row_anchor, compact_row, 1)
elif compact_row not in page:
    raise SystemExit("ERROR: OpenClash native file toolbar layout anchor changed")

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
	local restored, failure = false, "备份归档格式无法读取"
	local archive_fp = io.open(archive, "rb")
	local magic = archive_fp and archive_fp:read(2) or ""
	if archive_fp then archive_fp:close() end
	local gzip_archive = magic == "\31\139"
	local tar_list_options = gzip_archive and "tzf " or "tf "
	local tar_verbose_options = gzip_archive and "tvzf " or "tvf "
	local tar_extract_options = gzip_archive and "-xzf " or "-xf "
	local tarok = SYS.call("tar " .. tar_list_options .. quoted .. " >" .. listfile .. " 2>/dev/null") == 0
	local has_profile, unsafe = false, false
	local allowed, profiles, count = {}, {}, 0
	if tarok then
		for line in io.lines(listfile) do
			line = line:gsub("/$", "")
			if line:match("^/") or line:match("^%.%./") or line:find("/../", 1, true) or line:sub(-3) == "/.." then unsafe = true end
			local normalized = line:gsub("^%./", "")
			local category, name = normalized:match("^([%w_%-]+)/([^/]+)$")
			if name and not name:match("^[%w_.%-]+$") then unsafe = true end
			local ok = normalized == "openclash"
				or (category == "config" and name and name:match("%.ya?ml$"))
				or ((category == "custom" or category == "overwrite" or category == "proxy_provider" or category == "rule_provider") and name ~= nil)
				or normalized == "china_ip_route.ipset"
				or normalized == "china_ip6_route.ipset"
			if ok then
				count = count + 1
				if count > 2048 then unsafe = true; break end
				allowed[#allowed + 1] = line
				if category == "config" and name and name:match("%.ya?ml$") then
					has_profile = true
					profiles[#profiles + 1] = name
				end
			end
		end
	end
	local unsafe_allowed_types = SYS.call("tar " .. tar_verbose_options .. quoted .. " 2>/dev/null | grep -qE '^[lh].*[[:space:]](\\./)?(openclash|config(/[^[:space:]]*)?|custom(/[^[:space:]]*)?|overwrite(/[^[:space:]]*)?|proxy_provider(/[^[:space:]]*)?|rule_provider(/[^[:space:]]*)?|china_ip6?_route\\.ipset)([[:space:]]|$)'") == 0
	if tarok and has_profile and not unsafe and not unsafe_allowed_types then
		local allow = io.open(allowfile, "w")
		if allow then
			for index = 1, #allowed do allow:write(allowed[index], "\n") end
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
					table.sort(profiles)
					selected = profiles[1]
				end
				if selected and selected:match("^[%w_.%-]+%.ya?ml$") then
					local ok = SYS.call("mkdir -p /etc/openclash/config /etc/openclash/custom /etc/openclash/overwrite /etc/openclash/proxy_provider /etc/openclash/rule_provider") == 0
					SYS.call("uci set openclash.config.enable=0 && uci commit openclash && /etc/init.d/openclash stop >/dev/null 2>&1")
					local directories = {"config", "custom", "overwrite", "proxy_provider", "rule_provider"}
					for index = 1, #directories do
						local name = directories[index]
						local src = stage .. "/" .. name
						local dest = "/etc/openclash/" .. name
						if SYS.call("test -d " .. UTIL.shellquote(src)) == 0 then
							ok = ok and SYS.call("cp -f " .. UTIL.shellquote(src) .. "/* " .. UTIL.shellquote(dest .. "/")) == 0
						end
					end
					for index = 1, #profiles do
						local suffix = "/" .. profiles[index]
						ok = ok and SYS.call("test -s " .. UTIL.shellquote(config_dir .. suffix)
							.. " && cmp -s " .. UTIL.shellquote(config_dir .. suffix)
							.. " " .. UTIL.shellquote("/etc/openclash/config" .. suffix)) == 0
					end
					local route_files = {"china_ip_route.ipset", "china_ip6_route.ipset"}
					for index = 1, #route_files do
						local name = route_files[index]
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
					ok = ok and SYS.call("uci set openclash.config.enable=0 && uci set openclash.config.core_type=Meta && uci set openclash.config.core_version=linux-arm64 && uci set openclash.config.small_flash_memory=0 && uci set openclash.config.interface_name=br-lan && uci set openclash.config.lan_interface_name=br-lan && uci set openclash.config.en_mode=fake-ip-tun && uci set openclash.config.stack_type=system && uci set openclash.config.stack_type_v6=system && uci set openclash.config.smart_enable=0 && uci set openclash.config.auto_smart_switch=0 && uci set openclash.config.smart_enable_lgbm=0 && uci commit openclash") == 0
					restored = ok
					if not ok then failure = "配置或资源文件写入失败" end
				end
			else
				failure = "备份归档提取失败"
			end
		else
			failure = "备份内没有可用的 YAML 主配置"
		end
	elseif not tarok then
		failure = "备份不是有效的 TAR 或 TAR.GZ 归档"
	elseif unsafe or unsafe_allowed_types then
		failure = "备份包含不安全的路径或文件类型"
	end
	SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " " .. UTIL.shellquote(listfile) .. " " .. UTIL.shellquote(allowfile))
	return restored, failure, restored and profiles or nil
end
'''
lua.write_text(source[:start] + replacement + source[end:], encoding="utf-8")

controller_source = controller.read_text(encoding="utf-8")
session_anchor = 'local fs = require "luci.openclash"\n'
session_helper = r'''local function higoros_session_valid()
	local cookie = HTTP.getenv("HTTP_COOKIE") or ""
	local host = (HTTP.getenv("HTTP_HOST") or ""):lower():match("^([^:]+)")
	local origin = HTTP.getenv("HTTP_ORIGIN") or ""
	local referer = HTTP.getenv("HTTP_REFERER") or ""
	local source = origin ~= "" and origin or referer
	local source_host = source:lower():match("^https?://([^/:]+)")
	return #cookie > 0 and #cookie <= 8192 and host ~= nil and source_host == host
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
	local filename = HTTP.formvalue("filename") or ""
	local upload_type = HTTP.formvalue("upload_type") or ""
	if not id:match("^[a-f0-9]+$") or #id ~= 32 then return respond("error", "Invalid upload id") end
	if #filename == 0 or #filename > 240 or filename == "." or filename == ".." or filename:match("^%.") or filename:find("/", 1, true) or filename:find("\\", 1, true) or filename:find("%c") then return respond("error", "文件名无效：不能包含路径分隔符或控制字符") end
	local lower_filename = filename:lower()
	local types = {
		config = { dir = "/etc/openclash/config", suffix = lower_filename:match("%.ya?ml$") and true },
		["proxy-provider"] = { dir = "/etc/openclash/proxy_provider", suffix = lower_filename:match("%.ya?ml$") and true },
		["rule-provider"] = { dir = "/etc/openclash/rule_provider", suffix = lower_filename:match("%.ya?ml$") and true },
		clash_meta = { suffix = lower_filename:match("%.tar%.gz$") and true },
		["backup-file"] = { suffix = (lower_filename:match("%.tar%.gz$") or lower_filename:match("%.tar$")) and true }
	}
	if not types[upload_type] or not types[upload_type].suffix then return respond("error", "文件名后缀与上传类型不匹配") end
	local suffix = lower_filename:match("%.tar%.gz$") and ".tar.gz" or lower_filename:match("%.tar$") and ".tar" or ".upload"
	local path = "/tmp/higoos_openclash_" .. id .. suffix
	if operation == "start" then
		local fp = io.open(path, "wb")
		if not fp then return respond("error", "无法创建临时上传文件") end
		fp:close()
		return respond("success", "Upload started")
	elseif operation == "chunk" then
		local chunk = HTTP.content() or ""
		local offset = tonumber(HTTP.formvalue("offset") or "")
		if #chunk == 0 or #chunk > 65536 or not offset or offset < 0 then return respond("error", "上传数据块无效") end
		local fp = io.open(path, "r+b")
		if not fp then return respond("error", "上传已过期，请重新开始") end
		local current = fp:seek("end") or 0
		if current ~= offset or current + #chunk > 134217728 then fp:close(); return respond("error", "上传位置或文件大小无效") end
		fp:write(chunk)
		fp:close()
		return respond("success", "数据块已接收")
	elseif operation == "cancel" then
		fs.unlink(path)
		return respond("success", "上传已取消")
	elseif operation == "finish" then
		local fp = io.open(path, "rb")
		if not fp then return respond("error", "上传文件不存在") end
		local size = fp:seek("end") or 0
		fp:close()
		if size == 0 then fs.unlink(path); return respond("error", "上传文件为空") end
		if upload_type == "backup-file" then
			local ok, restored, reason = pcall(fs.restore_backup, path)
			fs.unlink(path)
			if not ok then return respond("error", "备份恢复错误：" .. tostring(restored):sub(1, 512)) end
			if not restored then return respond("error", tostring(reason or "备份文件无效或恢复失败")) end
			return respond("success", "备份已导入，OpenClash 保持关闭")
		elseif upload_type == "clash_meta" then
			local list = SYS.exec("tar -tzf " .. UTIL.shellquote(path) .. " 2>/dev/null") or ""
			local verbose = SYS.exec("tar -tvzf " .. UTIL.shellquote(path) .. " 2>/dev/null") or ""
			local core_member
			for member in list:gmatch("[^\r\n]+") do
				member = member:gsub("/$", "")
				if member == "./clash_meta" or member == "clash_meta" then core_member = member end
				if member:match("^/") or member:match("%.%./") or member:find("/../", 1, true) then fs.unlink(path); return respond("error", "内核压缩包包含不安全路径") end
			end
			local regular_core = false
			for line in verbose:gmatch("[^\r\n]+") do
				if line:sub(1, 1) == "-" and line:match("%s+%./?clash_meta$") then regular_core = true end
			end
			if not core_member or not regular_core then fs.unlink(path); return respond("error", "压缩包中未找到普通文件格式的 clash_meta 内核") end
			local stage = "/tmp/higoos_openclash_core_" .. id
			local allow = stage .. ".list"
			SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " && mkdir -p " .. UTIL.shellquote(stage))
			local list_fp = io.open(allow, "w")
			if list_fp then list_fp:write(core_member, "\n"); list_fp:close() end
			local extracted = list_fp and SYS.call("tar -C " .. UTIL.shellquote(stage) .. " -xzf " .. UTIL.shellquote(path) .. " -T " .. UTIL.shellquote(allow) .. " >/dev/null 2>&1") == 0
			local core_path = stage .. "/clash_meta"
			local core_fp = extracted and io.open(core_path, "rb")
			local header = core_fp and core_fp:read(20) or ""
			if core_fp then core_fp:close() end
			local arm64 = #header == 20 and header:byte(1) == 127 and header:sub(2, 4) == "ELF" and header:byte(5) == 2 and header:byte(6) == 1 and header:byte(19) == 183 and header:byte(20) == 0
			if not arm64 then SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " " .. UTIL.shellquote(allow)); fs.unlink(path); return respond("error", "内核文件不是 ARM64 Meta ELF，已拒绝安装") end
			local core_dir = meta_core_path:match("(.+)/[^/]+$") or "/etc/openclash/core"
			local ok = SYS.call("mkdir -p " .. UTIL.shellquote(core_dir) .. " && cp -f " .. UTIL.shellquote(core_path) .. " " .. UTIL.shellquote(meta_core_path) .. " && chmod 755 " .. UTIL.shellquote(meta_core_path)) == 0
			SYS.call("rm -rf " .. UTIL.shellquote(stage) .. " " .. UTIL.shellquote(allow)); fs.unlink(path)
			if not ok then return respond("error", "Meta 内核安装失败") end
			return respond("success", "ARM64 Meta 内核已安装")
		else
			local fp = io.open(path, "rb")
			local content = fp and fp:read(8192) or ""
			if fp then fp:close() end
			if upload_type == "config" and not (content:find("proxies:", 1, true) or content:find("proxy%-providers:") or content:find("rules:", 1, true) or content:find("port:", 1, true)) then fs.unlink(path); return respond("error", "配置文件缺少有效 YAML 配置段") end
			local target = types[upload_type].dir .. "/" .. filename
			local ok = SYS.call("mkdir -p " .. UTIL.shellquote(types[upload_type].dir) .. " && cp -f " .. UTIL.shellquote(path) .. " " .. UTIL.shellquote(target) .. " && chmod 644 " .. UTIL.shellquote(target)) == 0
			fs.unlink(path)
			if not ok then return respond("error", "文件保存失败") end
			return respond("success", "文件已保存到 " .. types[upload_type].dir)
		end
	end
	return respond("error", "Unsupported upload operation")
end
'''
upload_action_anchor = "\nfunction action_backup()"
if "function action_higoros_upload()" not in controller_source and controller_source.count(upload_action_anchor) == 1:
    controller_source = controller_source.replace(upload_action_anchor, "\n" + upload_action + upload_action_anchor, 1)
elif "function action_higoros_upload()" not in controller_source:
    raise SystemExit("ERROR: OpenClash upload action insertion anchor changed")

# The encrypted baseline already contains the first importer; update that handler in place too.
old_result = 'local ok, restored, reason = pcall(fs.restore_backup, path)'
old_success = 'return respond("success", "备份已导入，OpenClash 保持关闭")'
new_success = ('local count = #profiles\n'
               '\t\t\tlocal names = count <= 3 and "（" .. table.concat(profiles, "、") .. "）" or ""\n'
               '\t\t\treturn respond("success", "已恢复 " .. count .. " 份配置" .. names .. "，OpenClash 保持关闭")')
if controller_source.count(old_result) == 1 and controller_source.count(old_success) == 1:
    controller_source = controller_source.replace(old_result, old_result.replace("reason", "reason, profiles"), 1)
    controller_source = controller_source.replace(old_success, new_success, 1)
elif new_success not in controller_source:
    raise SystemExit("ERROR: OpenClash restore result hook changed")

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
