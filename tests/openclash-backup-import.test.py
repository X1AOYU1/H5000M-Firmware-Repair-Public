#!/usr/bin/env python3
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
page_source = (
    'const ma=el({setup(){const ve=g("config"),X=g(""),he=W(()=>true);'
    'async function Je(){return null}return()=>f.value==="files"?(o(),'
    'y("section",Hl,[s("div",Ql,[s("button",null)])])):null}});'
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
        subprocess.run([node, "--check", str(next(assets.glob("OpenClashPage-*.js")))], check=True)
    backend = lua.read_text(encoding="utf-8")
    endpoint = controller.read_text(encoding="utf-8")
    required_page = (
        'id:"oc-backup-file",type:"file",accept:backupFormat.value==="tar"?".tar,application/x-tar":".tar.gz,application/gzip",style:{display:"none"}',
        'document.getElementById("oc-backup-file")?.click()',
        'backupFile.value?.name||"未选择文件"',
        'async function downloadBackup()',
        'backupFormat=g("tar.gz")',
        'backup_type:"backup"',
        '上传文件类型',
        '备份文件 (.tar.gz)',
        '备份文件 (.tar)',
        '选择文件',
        '未选择文件',
        '上传',
        'd("备份")',
        'class:"flex flex-wrap items-center gap-2"',
        'application/octet-stream',
        'body:file.slice(offset,offset+1048576)',
        'params.operation==="download"?"backup":"upload"',
        '/cgi-bin/luci/higoros/openclash/',
    )
    required_backend = (
        'local allowfile = "/tmp/oc_restore.allow"',
        'category == "rule_provider"',
        'uci set openclash.config.core_type=Meta',
        'uci set openclash.config.interface_name=br-lan',
        'uci set openclash.config.enable=0',
        'china_ip6_route.ipset',
    )
    if any(marker not in page for marker in required_page):
        raise SystemExit("ERROR: HigoOS OpenClash backup upload UI is incomplete")
    if any(marker not in backend for marker in required_backend):
        raise SystemExit("ERROR: filtered H5000M backup restore is incomplete")
    if page.count("async function uploadBackup()") != 1 or page.count('d("上传",-1)') != 1 or page.count('d("备份")') != 1:
        raise SystemExit("ERROR: repeated backup patching duplicated the importer")
    if 'await $.saveFile(' in page or 'oc-backup-upload-frame' in page or 'restore_token_file' in page:
        raise SystemExit("ERROR: backup upload still depends on unsupported custom-file authorization")
    if page.count('id:"oc-backup-file"') != 1 or page.count('||"未选择文件"') != 1:
        raise SystemExit("ERROR: backup file picker is duplicated or not custom-rendered")
    if page.count('class:"flex flex-wrap items-center gap-2"') != 1:
        raise SystemExit("ERROR: backup controls are not grouped in one responsive HigoOS toolbar")
    if 'id:"oc-backup-file",type:"file",accept:".tar,.tar.gz,application/x-tar,application/gzip",disabled:' in page:
        raise SystemExit("ERROR: upload state disables the native file field before form submission")
    if "Backup archive exceeds 128 MiB limit" not in endpoint:
        raise SystemExit("ERROR: backup upload size limit was not installed")
    if 'function action_higoros_upload()' not in endpoint or 'HTTP.content()' not in endpoint or 'current ~= offset' not in endpoint or 'higoros_upload_entry.sysauth = false' not in endpoint or 'entry({"higoros", "openclash", "upload"}' not in endpoint:
        raise SystemExit("ERROR: raw chunked backup upload endpoint is incomplete")
    if 'entry({"higoros", "openclash", "backup"}' not in endpoint or 'higoros_backup_entry.sysauth = false' not in endpoint:
        raise SystemExit("ERROR: backup download endpoint is still behind the LuCI admin route")
    if 'pcall(fs.restore_backup, target_path)' not in endpoint or 'Backup restore error: ' not in endpoint:
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
    if 'tar_list_options = gzip_archive and "tzf " or "tf "' not in backend or 'tar_extract_options = gzip_archive and "-xzf " or "-xf "' not in backend:
        raise SystemExit("ERROR: .tar and .tar.gz extraction modes are incomplete")
    if "core/" in backend or "GeoIP.dat" in backend or "Model.bin" in backend:
        raise SystemExit("ERROR: filtered restore includes donor core, geo, or Smart model data")

print("PASS: HigoOS backup upload is idempotent and restore filters incompatible donor assets")
