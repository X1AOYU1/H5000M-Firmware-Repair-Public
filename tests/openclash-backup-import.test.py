#!/usr/bin/env python3
from pathlib import Path
import io
import subprocess
import shutil
import sys
import tempfile
import re
import tarfile


repo = Path(__file__).resolve().parents[1]


def check_restore_archive_format(temporary):
    members = {
        "./openclash": b"config openclash 'config'\n option config_path '/etc/openclash/config/main.yaml'\n",
        "./config/main.yaml": b"proxies: []\nproxy-groups: []\nrules: [MATCH,DIRECT]\n",
        "./custom/custom_rules.list": b"",
        "./core/clash_meta": b"incompatible donor core",
    }
    for suffix, mode in (("tar", "w"), ("tar.gz", "w:gz")):
        archive = Path(temporary) / f"openclash-fixture.{suffix}"
        with tarfile.open(archive, mode) as output:
            for name, body in members.items():
                item = tarfile.TarInfo(name)
                item.size = len(body)
                output.addfile(item, io.BytesIO(body))
            link = tarfile.TarInfo("./clash")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/openclash/core/clash_meta"
            output.addfile(link)
        with tarfile.open(archive, "r:*") as source:
            names = [entry.name.rstrip("/") for entry in source]
        normalized = [name.removeprefix("./") for name in names]
        assert "openclash" in normalized
        assert "config/main.yaml" in normalized
        assert "core/clash_meta" in normalized
        assert "clash" in normalized
        assert (archive.read_bytes()[:2] == b"\x1f\x8b") == suffix.endswith(".gz")


page_source = (
    'const Ql={class:"flex flex-wrap gap-3"};const ma=el({setup(){const ve=g("config"),X=g(""),he=W(()=>true);'
    'async function Je(){return null}return()=>f.value==="files"?(o(),'
    'y("section",Hl,[s("div",Ql,[ie(s("select",{"onUpdate:modelValue":e[9]||(e[9]=l=>ve.value=l),"aria-label":"新建类型",class:"rounded border border-line-1/70 bg-bg-2/50 p-2"},[],512),[[sl,ve.value]]),ie(s("input",{"onUpdate:modelValue":e[10]||(e[10]=l=>X.value=l),placeholder:"文件名.yaml",class:"rounded border border-line-1/70 bg-bg-2/50 p-2"},null,512),[[ye,X.value]]),m(i(p),{variant:"secondary",disabled:t.value||!X.value.trim(),onClick:Je},{default:r(()=>[...e[49]||(e[49]=[d("新建文件",-1)])]),_:1},8,["disabled"])])])):null}});'
)
lua_source = (
    'function restore_backup(archive)\n\treturn false\nend\n'
    'function get_age_keys(file)\n\treturn {}\nend\n'
)
controller_source = (
    'local SYS = require "luci.sys"\n'
    'local HTTP = require "luci.http"\n'
    'local UTIL = require "luci.util"\n'
    'local fs = require "luci.openclash"\n'
    'function index()\n'
    '\tentry({"admin", "services", "openclash", "backup"}, call("action_backup"))\n'
    '\tentry({"admin", "services", "openclash", "restore_backup"}, call("action_restore_backup"))\n'
    'end\n'
    'function action_backup()\nend\n'
    'function action_backup_ex_core()\nend\n'
    'function action_backup_only_config()\nend\n'
    'function action_backup_only_rule()\nend\n'
    'function action_backup_only_proxy()\nend\n'
    'function action_backup_only_core()\nend\n'
    'function action_restore_backup()\n'
    '\tlocal started, fp, target_path, stream_err = false, nil, nil, nil\n'
    '\t\t\tstarted = true\n\n\t\t\tlocal name = (meta and meta.file) or ""\n'
    '\tlocal restored = fs.restore_backup(target_path)\n'
    '\tfs.unlink(target_path)\n'
    '\tif restored then\n\t\tHTTP.write_json({\n'
    '\t\t\ttarget_path = backup_dir .. name\n'
    '\t\tif chunk and fp then\n\t\t\tfp:write(chunk)\n\t\tend\n'
    '\tif stream_err then\n\t\tif target_path then\n'
    '\t\t\tfs.unlink(target_path)\n\t\tend\n\tend\nend\n'
    'function action_config_file_read()\nend\n'
)

with tempfile.TemporaryDirectory() as temporary:
    check_restore_archive_format(temporary)
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    (assets / "OpenClashPage-fixture.js").write_text(page_source, encoding="utf-8")
    lua = root / "usr/lib/lua/luci/openclash.lua"
    lua.parent.mkdir(parents=True)
    lua.write_text(lua_source, encoding="utf-8")
    controller = root / "usr/lib/lua/luci/controller/openclash.lua"
    controller.parent.mkdir(parents=True)
    controller.write_text(controller_source, encoding="utf-8")

    patcher = repo / "scripts/patch-higoros-openclash-backup-import.py"
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)

    page = next(assets.glob("OpenClashPage-*.js")).read_text(encoding="utf-8")
    node = shutil.which("node")
    if node:
        checked_page = next(assets.glob("OpenClashPage-*.js"))
        check = subprocess.run([node, "--check", str(checked_page)], text=True, encoding="utf-8", capture_output=True)
        if check.returncode:
            generated = checked_page.read_text(encoding="utf-8")
            (repo / "OpenClashPage-fixture.debug.js").write_text(generated, encoding="utf-8")
            raise SystemExit(check.stderr or check.stdout or "Node.js rejected the patched OpenClash page")
    backend = lua.read_text(encoding="utf-8")
    endpoint = controller.read_text(encoding="utf-8")
    user_backup_name = "Backup-OpenClash-Hiveton H5000M-aarch64-2026-11-20-14-47-56.tar"
    if not re.search(r"\.tar(?:\.gz)?$", user_backup_name, re.IGNORECASE) or len(user_backup_name.encode("utf-8")) > 240 or any(char in user_backup_name for char in "/\\") or any(ord(char) < 32 or ord(char) == 127 for char in user_backup_name):
        raise SystemExit("ERROR: the supplied H5000M .tar backup filename is not accepted")
    required_page = (
        'id:"oc-backup-file-type",value:uploadType.value',
        '"aria-label":"上传文件类型"',
        'uploadType=g("config")',
        'value:"config"}',
        'value:"proxy-provider"}',
        'value:"rule-provider"}',
        'value:"clash_meta"}',
        'value:"backup-file"}',
        'value:"config"},"配置文件 (.yaml)"',
        'value:"proxy-provider"},"代理文件"',
        'value:"rule-provider"},"规则集文件"',
        'value:"clash_meta"},"[Meta] 内核文件 (.tar.gz)"',
        'value:"backup-file"},"备份文件 (.tar.gz)"',
        'uploadType.value==="backup-file"||uploadType.value==="clash_meta"',
        'id:"oc-backup-file",type:"file",accept:uploadType.value==="config"||uploadType.value==="proxy-provider"||uploadType.value==="rule-provider"?".yaml,.yml":uploadType.value==="backup-file"?".tar,.tar.gz,application/x-tar,application/gzip":".tar.gz,application/gzip",style:{display:"none"}',
        'file.name):uploadType.value==="clash_meta"',
        'valid=uploadType.value==="backup-file"? /\\.tar(?:\\.gz)?$/i.test(file.name)',
        'document.getElementById("oc-backup-file")?.click()',
        'backupFile.value?.name||"未选择文件"',
        'async function downloadBackup()',
        'raw.replace(/<!--[\\s\\S]*?-->/g," ")',
        'replace(/<style[^]*?[/]style>/gi," ")',
        'backup_type:"backup"',
        '上传文件类型：',
        'aria-label":"新建文件类型"',
        '选择文件',
        '未选择文件',
        'd("上传",-1)',
        'd("备份")',
        'onClick:downloadBackup',
        'fontSize:"14px"',
        'class:"w-44 h-9 shrink-0 truncate rounded border border-line-1/70 bg-bg-2/50 px-2 py-1 text-sm text-muted"',
        'class:"w-52 h-9 shrink-0 rounded border border-line-1/70 bg-bg-2/50 px-2 text-sm"',
        'Ql={class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto"}',
        'application/octet-stream',
        'body:file.slice(offset,offset+65536)',
        'params.operation==="download"?"backup":"upload"',
        '/cgi-bin/luci/higoros/openclash/',
    )
    required_backend = (
        'local allowfile = "/tmp/oc_restore.allow"',
        'category == "rule_provider"',
        'uci set openclash.config.core_type=Meta',
        'uci set openclash.config.core_version=linux-arm64',
        'uci set openclash.config.small_flash_memory=0',
        'uci set openclash.config.interface_name=br-lan',
        'uci set openclash.config.enable=0',
        'uci set openclash.config.stack_type=system',
        'uci set openclash.config.stack_type_v6=system',
        'china_ip6_route.ipset',
    )
    if any(marker not in page for marker in required_page):
        raise SystemExit("ERROR: HigoOS OpenClash backup upload UI is incomplete: " + ", ".join(marker for marker in required_page if marker not in page))
    if any(marker not in backend for marker in required_backend):
        raise SystemExit("ERROR: filtered H5000M backup restore is incomplete")
    if page.count("async function uploadBackup()") != 1 or page.count('d("上传",-1)') != 1 or page.count('d("备份")') != 1:
        raise SystemExit("ERROR: repeated backup patching duplicated the importer")
    if 'await $.saveFile(' in page or 'oc-backup-upload-frame' in page or 'restore_token_file' in page:
        raise SystemExit("ERROR: backup upload still depends on unsupported custom-file authorization")
    if page.count('id:"oc-backup-file"') != 1 or page.count('||"未选择文件"') != 1:
        raise SystemExit("ERROR: backup file picker is duplicated or not custom-rendered")
    if page.count('"aria-label":"上传文件类型"') != 1:
        raise SystemExit("ERROR: upload file-type menu is missing or duplicated")
    if any(marker in page for marker in ('value:"backup-download"', 'value:"create-config"', 'value:"create-overwrite"', 'value:"create-proxy-provider"', 'value:"create-rule-provider"', 'value:"create-custom"')):
        raise SystemExit("ERROR: upload dropdown contains unrelated backup-download or file-creation choices")
    if page.count('"aria-label":"新建类型"') != 0:
        raise SystemExit("ERROR: duplicate new-file type menu remains")
    if page.count('id:"oc-backup-file-type"') != 1:
        raise SystemExit("ERROR: unified operation menu control is duplicated")
    if page.count('Ql={class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto"}') != 1 or '配置文件保存在配置目录（/etc/openclash/config）' in page:
        raise SystemExit("ERROR: OpenClash operation controls do not use the native compact row")
    if page.count('s("div",Ql,[') != 1 or 's("div",{class:"flex w-full flex-wrap' in page:
        raise SystemExit("ERROR: OpenClash file creation and upload controls are not in one row")
    if 'id:"oc-backup-file",type:"file",accept:".tar,.tar.gz,application/x-tar,application/gzip",disabled:' in page:
        raise SystemExit("ERROR: upload state disables the native file field before form submission")
    if "Backup archive exceeds 128 MiB limit" not in endpoint:
        raise SystemExit("ERROR: backup upload size limit was not installed")
    if 'function action_higoros_upload()' not in endpoint or 'HTTP.content()' not in endpoint or 'current ~= offset' not in endpoint or '#chunk > 65536' not in endpoint or 'lower_filename = filename:lower()' not in endpoint or 'filename:find("/", 1, true)' not in endpoint or 'filename:find("\\\\", 1, true)' not in endpoint or 'higoros_upload_entry.sysauth = false' not in endpoint or 'entry({"higoros", "openclash", "upload"}' not in endpoint or 'config = { dir = "/etc/openclash/config"' not in endpoint or 'clash_meta = { suffix = lower_filename:match("%.tar%.gz$") and true }' not in endpoint or 'lower_filename:match("%.tar$")' not in endpoint or 'local suffix = lower_filename:match("%.tar%.gz$") and ".tar.gz" or lower_filename:match("%.tar$") and ".tar" or ".upload"' not in endpoint or 'header:byte(19) == 183' not in endpoint:
        raise SystemExit("ERROR: native file type upload endpoint is incomplete")
    if 'entry({"higoros", "openclash", "backup"}' not in endpoint or 'higoros_backup_entry.sysauth = false' not in endpoint:
        raise SystemExit("ERROR: backup download endpoint is still behind the LuCI admin route")
    if 'pcall(fs.restore_backup, target_path)' not in endpoint or 'Backup restore error: ' not in endpoint or 'tostring(reason or "备份文件无效或恢复失败")' not in endpoint:
        raise SystemExit("ERROR: restore exceptions are not converted to a JSON response")
    if 'oc_restore_entry.sysauth = false' not in endpoint or 'higoros_backup_entry.sysauth = false' not in endpoint or 'HTTP.getenv("HTTP_COOKIE")' not in endpoint or 'HigoOS session is invalid or expired' not in endpoint:
        raise SystemExit("ERROR: HigoOS cookie-session authorization is incomplete")
    if 'HTTP.getenv("HTTP_ORIGIN")' not in endpoint or 'HTTP.getenv("HTTP_REFERER")' not in endpoint or 'source_host == host' not in endpoint or '#cookie > 0' not in endpoint or 'cookie:find(' in endpoint or 'curl --noproxy' in endpoint:
        raise SystemExit("ERROR: HigoOS session validation does not check same-origin cookie requests")
    backup_actions = (
        'backup = action_backup',
        'backup_ex_core = action_backup_ex_core',
        'backup_only_config = action_backup_only_config',
        'backup_only_rule = action_backup_only_rule',
        'backup_only_proxy = action_backup_only_proxy',
        'backup_only_core = action_backup_only_core',
    )
    if 'function action_higoros_backup()' not in endpoint or any(action not in endpoint for action in backup_actions):
        raise SystemExit("ERROR: native backup generation options are not exposed to HigoOS")
    if 'Backup must be a .tar or .tar.gz archive' not in endpoint:
        raise SystemExit("ERROR: .tar backup support is missing")
    if 'filename:find("/", 1, true)' not in endpoint or 'filename:find("\\\\", 1, true)' not in endpoint:
        raise SystemExit("ERROR: backup filename validation rejects normal names or permits unsafe paths")
    if 'tar_list_options = gzip_archive and "tzf " or "tf "' not in backend or 'tar_extract_options = gzip_archive and "-xzf " or "-xf "' not in backend:
        raise SystemExit("ERROR: .tar and .tar.gz extraction modes are incomplete")
    if r'local gzip_archive = magic == "\31\139"' not in backend or 'local normalized = line:gsub("^%./", "")' not in backend or 'local unsafe_allowed_types = SYS.call' not in backend:
        raise SystemExit("ERROR: restore does not detect actual archive format and filter donor core links safely")
    if "ipairs(" in backend or 'for index = 1, #allowed do' not in backend or 'for index = 1, #directories do' not in backend or 'for index = 1, #route_files do' not in backend:
        raise SystemExit("ERROR: restore depends on unavailable ipairs instead of Lua numeric iteration")
    if "core/" in backend or "GeoIP.dat" in backend or "Model.bin" in backend:
        raise SystemExit("ERROR: filtered restore includes donor core, geo, or Smart model data")
    if 'uci -q delete openclash.config.stack_type' in backend:
        raise SystemExit("ERROR: H5000M restore deletes stack_type and falls back to OpenClash's MIPS default")

print("PASS: HigoOS backup upload is idempotent and restore filters incompatible donor assets")
