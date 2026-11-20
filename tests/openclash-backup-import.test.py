#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
page_source = (
    'const ma=el({setup(){const ve=g("config"),X=g(""),he=W(()=>true);'
    'async function Je(){return null}return()=>f.value==="files"?(o(),'
    'y("section",Hl,[s("div",Ql,[s("button",null)]))}});'
)
lua_source = (
    'function restore_backup(archive)\n\treturn false\nend\n'
    'function get_age_keys(file)\n\treturn {}\nend\n'
)
controller_source = (
    'function index()\n'
    '\tentry({"admin", "services", "openclash", "restore_backup"}, call("action_restore_backup"))\n'
    'end\n'
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
    backend = lua.read_text(encoding="utf-8")
    endpoint = controller.read_text(encoding="utf-8")
    required_page = (
        'id:"oc-backup-file",type:"file",accept:".tar.gz,application/gzip",style:{display:"none"}',
        'document.getElementById("oc-backup-file")?.click()',
        'backupFile.value?.name||"选择备份文件"',
        'form.enctype="multipart/form-data"',
        'form.target=frame.name',
        'input.disabled=!1;form.submit()',
        'await $.saveFile({...ticket,category:"custom",name:ticketName,content:token,activate:!1})',
        'tokenField.name="restore_token"',
        'ticketField.name="restore_token_file"',
        'const ready=new Promise((resolve,reject)=>{const initTimer=setTimeout(()=>reject(new Error("无法初始化备份上传窗口")),10000);frame.onload=()=>{clearTimeout(initTimer);resolve()}});document.body.append(frame,form);await ready;',
        'snapshot=rows=>JSON.stringify(rows.filter(row=>row.name!==ticketName).map(row=>[row.category,row.name,row.size]))',
        'before=snapshot(ke.value)',
        'const after=snapshot(ke.value)',
        '上传等待超时，请检查路由器连接后重试',
        'HigoOS 未检测到备份文件变化',
        '导入 OpenClash 备份 (.tar.gz)',
        '/cgi-bin/luci/admin/services/openclash/restore_backup',
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
    if page.count("async function uploadBackup()") != 1 or page.count('导入 OpenClash 备份 (.tar.gz)') != 1:
        raise SystemExit("ERROR: repeated backup patching duplicated the importer")
    if "fetch(\"/cgi-bin/luci/admin/services/openclash/restore_backup\"" in page:
        raise SystemExit("ERROR: backup upload still uses fetch against the LuCI CGI endpoint")
    if "frame.contentDocument" in page:
        raise SystemExit("ERROR: backup upload response still assumes the LuCI frame is same-origin")
    if page.index('frame.onload=()=>{clearTimeout(initTimer);resolve()}') > page.index('document.body.append(frame,form)'):
        raise SystemExit("ERROR: backup iframe load handler is registered after insertion")
    if page.count('id:"oc-backup-file"') != 1 or page.count('||"选择备份文件"') != 1:
        raise SystemExit("ERROR: backup file picker is duplicated or not custom-rendered")
    if 'id:"oc-backup-file",type:"file",accept:".tar.gz,application/gzip",disabled:' in page:
        raise SystemExit("ERROR: upload state disables the native file field before form submission")
    if "Backup archive exceeds 128 MiB limit" not in endpoint:
        raise SystemExit("ERROR: backup upload size limit was not installed")
    if 'pcall(fs.restore_backup, target_path)' not in endpoint or 'Backup restore error: ' not in endpoint:
        raise SystemExit("ERROR: restore exceptions are not converted to a JSON response")
    if 'oc_restore_entry.sysauth = false' not in endpoint or 'HigoOS authorization token is invalid or expired' not in endpoint:
        raise SystemExit("ERROR: protected HigoOS one-time upload authorization is incomplete")
    if "core/" in backend or "GeoIP.dat" in backend or "Model.bin" in backend:
        raise SystemExit("ERROR: filtered restore includes donor core, geo, or Smart model data")

print("PASS: HigoOS backup upload is idempotent and restore filters incompatible donor assets")
