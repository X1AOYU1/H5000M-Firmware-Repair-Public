#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:?usage: build-public-node-free-wallpaper.sh full-repair-base.bin output-dir}"
OUT="${2:?missing output directory}"
EXPECTED="0ef1a767462ea78271d67388421dda5de3b4097a5a786db47dc75276130492e4"
mkdir -p "$OUT/tar" "$OUT/rootfs"
actual="$(sha256sum "$IMAGE" | awk '{print $1}')"
[[ "$actual" == "$EXPECTED" ]] || { echo "ERROR: full-repair base firmware SHA256 mismatch"; exit 2; }
tar -xf "$IMAGE" -C "$OUT/tar"
root="$(find "$OUT/tar" -type f -name root -print -quit)"
[[ -n "$root" ]] || { echo "ERROR: firmware root SquashFS missing"; exit 3; }
unsquashfs -no-progress -d "$OUT/rootfs" "$root" >/dev/null

python3 scripts/clean-public-openclash-config.py "$OUT/rootfs" | tee "$OUT/openclash-node-cleanup.txt"
python3 scripts/patch-higoros-openclash-backup-import.py "$OUT/rootfs" | tee "$OUT/openclash-backup-import.txt"
python3 scripts/patch-higoros-openclash-proxy-select.py "$OUT/rootfs" | tee "$OUT/openclash-proxy-select.txt"
python3 scripts/patch-higoros-openclash-entry.py "$OUT/rootfs" | tee "$OUT/openclash-entry-route.txt"
python3 scripts/patch-native-openclash-ui.py "$OUT/rootfs" | tee "$OUT/native-openclash-ui.txt"
python3 scripts/patch-higoros-openclash-bulk-latency.py "$OUT/rootfs" | tee "$OUT/openclash-bulk-latency.txt"
python3 scripts/patch-openclash-meta-core-link.py "$OUT/rootfs" | tee "$OUT/openclash-meta-core-link.txt"

# Apply the current login-page fix and revise every SPA asset URL afterward.
python3 scripts/patch-higoros-login-wallpaper.py "$OUT/rootfs" | tee "$OUT/login-wallpaper-fix.txt"
python3 scripts/revision-higoros-web-assets.py "$OUT/rootfs" | tee "$OUT/frontend-asset-revision.txt"

python3 - "$OUT/rootfs" <<'PY'
from pathlib import Path
import re
import sys
import yaml

root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
login = next(assets.glob("LoginPage-*.js")).read_text(encoding="utf-8")
native = next(assets.glob("NativeConfigSection*.js")).read_text(encoding="utf-8")
network = next(assets.glob("NetworkPage-*.js")).read_text(encoding="utf-8")
security = next(assets.glob("SecurityPage-*.js")).read_text(encoding="utf-8")
next(assets.glob("SystemPage-*.js"))
openclash_page = next(assets.glob("OpenClashPage-*.js"))
openclash_lua = (root / "usr/lib/lua/luci/openclash.lua").read_text(encoding="utf-8")
openclash_subscribe = (root / "usr/share/openclash/openclash.sh").read_text(encoding="utf-8")
openclash_core_update = (root / "usr/share/openclash/openclash_core.sh").read_text(encoding="utf-8")
openclash_controller = (root / "usr/lib/lua/luci/controller/openclash.lua").read_text(encoding="utf-8")
plugin_page = next(assets.glob("PluginsPage-*.js")).read_text(encoding="utf-8")
router_asset = next((path for path in assets.glob("index-*.js") if 'path:"apps/openclash"' in path.read_text(encoding="utf-8")), None)
if router_asset is None:
    raise SystemExit("ERROR: HigoOS OpenClash route is not registered")
app_router = router_asset.read_text(encoding="utf-8")
package = next((assets.glob("PackagesPage-*.js")), None)
crop_modules = list(assets.glob("higoos-wallpaper-crop-*.js"))
checks = {
    "login wallpaper image rendering": "higoos-login-wallpaper." in login and 'wallpaper.value?i("img",{src:wallpaper.value' in login,
    "login card translucency preserves contrast": 'card.style.setProperty("background-color","rgba(255,255,255,.84)"' in login and 'input[type="password"]' in login and 'new MutationObserver(q)' in login,
    "wallpaper upload cache reset": 'localStorage.removeItem("higoos_argon_login_wallpaper_source")' in native,
    "Argon upload publication": 'new File([blob],aliasName' in native,
    "wallpaper crop module is imported": len(crop_modules) == 1 and re.search(r'import\{mountHigoosWallpaperCrop\}from"\./higoos-wallpaper-crop-h5000m[a-f0-9]+\.js";', native) is not None,
    "wallpaper crop controls and upload": len(crop_modules) == 1 and all(value in crop_modules[0].read_text(encoding="utf-8") for value in ("pointermove", 'data-control="zoom"', "保存裁切并应用", "canvas.toBlob", "await upload(output)")),
    "original HigoOS OpenClash page retained": openclash_page.stat().st_size > 1000 and 'y("iframe"' not in openclash_page.read_text(encoding="utf-8"),
    "OpenClash app-center button embeds native LuCI": 'to:{path:"/apps/openclash-luci"}' in plugin_page and 'path:"apps/openclash-luci"' in app_router and 'entry({"admin", "services", "openclash"}' in openclash_controller and (root / "www/cgi-bin/luci").is_file(),
    "OpenClash runtime one-click latency test": all(value in openclash_page.read_text(encoding="utf-8") for value in ("一键测速", "h5000mRunAllLatency", "Math.min(5,h5000mNodes.length)", "h5000mBulkProgress", '"test-latency",name', 'de.value[String(result.name)]')) and openclash_page.read_text(encoding="utf-8").count("h5000mRunAllLatency") == 2,
    "OpenClash manual selection readback recovery": all(value in openclash_page.read_text(encoding="utf-8") for value in ("h5000mConfirmProxySelection", 'includes("节点选择回读不一致")', 'selected?.now===name')) and openclash_page.read_text(encoding="utf-8").count("async function h5000mConfirmProxySelection(") == 1,
    "Meta core canonical executable link repaired": all(value in openclash_subscribe for value in ('ensure_meta_core_compat_link()', 'ensure_meta_core_compat_link || {', '/etc/openclash/core/clash_meta', '/tmp/etc/openclash/core/clash_meta')) and 'ln -s "$TARGET_CORE_PATH" /etc/openclash/clash' in openclash_core_update,
    "WAN and IPv6 edit controls": all(value in network for value in ('key:"dhcp"', 'key:"static"', 'key:"pppoe"', 'key:"ds-lite"', "ipv6Types", "saveWANConfig", "saveIPv6Config")),
    "password policy controls": all(value in security for value in ("requireNumber", "requireLowercase", "requireUppercase", "requireSpecialChar", "密码策略已保存")),
    "appearance settings UI": package is not None and "LuCI" in package.read_text(encoding="utf-8"),
    "package market UI": package is not None,
}
upload_ui = (
    'id:"oc-backup-file-type"' in openclash_page.read_text(encoding="utf-8")
    and all(value in openclash_page.read_text(encoding="utf-8") for value in (
        '"aria-label":"上传文件类型"',
        'value:"config"},"配置文件 (.yaml)"',
        'value:"proxy-provider"},"代理文件"',
        'value:"rule-provider"},"规则集文件"',
        'value:"clash_meta"},"[Meta] 内核文件 (.tar.gz)"',
        'value:"backup-file"},"备份文件 (.tar.gz)"', 'value:"create-file"},"新建文件"', '选择文件', '未选择文件', '上传', '备份',
        'fontSize:"14px"', 'text-sm',
        'Ql={class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto"}',
        'body:file.slice(offset,offset+65536)',
    ))
    and '"aria-label":"新建文件类型"' in openclash_page.read_text(encoding="utf-8")
    and 'style:{display:uploadType.value==="create-file"?"":"none"}' in openclash_page.read_text(encoding="utf-8")
    and all(value not in openclash_page.read_text(encoding="utf-8") for value in ('value:"backup-download"', 'value:"create-config"', 'value:"create-overwrite"', 'value:"create-proxy-provider"', 'value:"create-rule-provider"', 'value:"create-custom"'))
    and 'class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto",style:' not in openclash_page.read_text(encoding="utf-8")
    and '配置文件保存在配置目录（/etc/openclash/config）' not in openclash_page.read_text(encoding="utf-8")
)
upload_backend = all(value in openclash_controller for value in (
    'function action_higoros_backup()', 'function action_higoros_upload()',
    'HTTP.getenv("HTTP_COOKIE")', 'HTTP.getenv("HTTP_ORIGIN")',
    'HTTP.getenv("HTTP_REFERER")', 'HTTP.content()', '#chunk > 65536',
    'Backup archive exceeds 128 MiB limit',
)) and all(value in openclash_lua for value in (
    'local allowfile = "/tmp/oc_restore.allow"',
    'uci set openclash.config.core_type=Meta',
    'uci set openclash.config.core_version=linux-arm64',
    'uci set openclash.config.small_flash_memory=0',
    'uci set openclash.config.stack_type=system',
    'uci set openclash.config.stack_type_v6=system',
    'uci set openclash.config.enable=0',
))
checks["HigoOS single-row upload, backup, and safe restore"] = upload_ui and upload_backend
for label, passed in checks.items():
    if not passed:
        raise SystemExit(f"ERROR: complete-repair feature missing after node cleanup: {label}")
    print(f"PASS: retained complete-repair feature: {label}")

oc = root / "etc/openclash"
profile = yaml.safe_load((oc / "config/config.yaml").read_text(encoding="utf-8"))
if profile.get("proxies") != [] or profile.get("proxy-groups") != [] or profile.get("rules") != ["MATCH,DIRECT"]:
    raise SystemExit("ERROR: clean OpenClash starter profile is invalid")
for name in ("127.0.0.1.yaml", "dy.yaml"):
    if (oc / "config" / name).exists():
        raise SystemExit(f"ERROR: requested OpenClash profile remains: {name}")
for path in oc.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml", ".conf", ".json", ".txt", ".sh", ".list", ".dat"}:
        continue
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        continue
    is_profile = path.is_relative_to(oc / "config") or path.is_relative_to(oc / "backup")
    sensitive = r"(?i)(?:password|passwd|secret|token|uuid)\s*[:=]\s*[^\s,'\"]+|(?:vmess|vless|trojan|ss)://"
    if not is_profile and re.search(sensitive, body):
        raise SystemExit(f"ERROR: possible proxy credential remains in public image: {path.relative_to(root)}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(body)
        if isinstance(data, dict):
            if data.get("proxies") or data.get("proxy-providers"):
                raise SystemExit(f"ERROR: proxy nodes or providers remain in {path.relative_to(root)}")
            group_names = {item.get("name") for item in data.get("proxy-groups", []) if isinstance(item, dict) and item.get("name")}
            builtins = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "GLOBAL"}
            for group in data.get("proxy-groups", []):
                if not isinstance(group, dict):
                    continue
                if set(group.get("use", [])):
                    raise SystemExit(f"ERROR: proxy provider references remain in {path.relative_to(root)}")
                refs = set(group.get("proxies", []))
                if refs - group_names - builtins:
                    raise SystemExit(f"ERROR: node references remain in proxy groups in {path.relative_to(root)}")
print("PASS: only the empty OpenClash starter config remains; node definitions, group references, providers, backups, and subscription credentials are absent")
PY

login_asset="$(find "$OUT/rootfs/usr/share/higoros/web/assets" -maxdepth 1 -type f -name 'LoginPage-*.js' -print -quit)"
node --check "$login_asset"
openclash_asset="$(find "$OUT/rootfs/usr/share/higoros/web/assets" -maxdepth 1 -type f -name 'OpenClashPage-*.js' -print -quit)"
node --check "$openclash_asset"
plugins_asset="$(find "$OUT/rootfs/usr/share/higoros/web/assets" -maxdepth 1 -type f -name 'PluginsPage-*.js' -print -quit)"
node --check "$plugins_asset"
new_root="$OUT/rootfs.repaired"
mksquashfs "$OUT/rootfs" "$new_root" -noappend -comp xz -b 262144 -no-xattrs -processors 2 >/dev/null
python3 - "$IMAGE" "$root" "$new_root" "$OUT/repaired.tar" <<'PY'
import os
import sys
import tarfile
source, old_root, new_root, output = sys.argv[1:]
with tarfile.open(source, "r:*") as archive:
    members = archive.getmembers()
    target = next((member for member in members if member.name == "root" or member.name.endswith("/root")), None)
    if target is None:
        raise SystemExit("ERROR: root member not found")
    with tarfile.open(output, "w", format=tarfile.USTAR_FORMAT) as packed:
        for member in members:
            if member.name != target.name:
                packed.addfile(member, archive.extractfile(member) if member.isfile() else None)
                continue
            info = tarfile.TarInfo(member.name)
            for field in ("mode", "uid", "gid", "uname", "gname", "mtime", "type", "linkname", "devmajor", "devminor", "pax_headers"):
                setattr(info, field, getattr(member, field))
            info.size = os.path.getsize(new_root)
            with open(new_root, "rb") as stream:
                packed.addfile(info, stream)
PY
cp "$OUT/repaired.tar" "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin"
cat > "$OUT/metadata.json" <<'JSON'
{ "metadata_version": "1.1", "compat_version": "1.0", "supported_devices": ["hiveton,h5000m", "hiveton-h5000m"], "version": { "dist": "ImmortalWrt", "version": "24.10-SNAPSHOT", "revision": "unknown", "target": "mediatek/filogic", "board": "hiveton,h5000m" } }
JSON
fwtool -I "$OUT/metadata.json" "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin"
fwtool -i "$OUT/metadata-extracted.json" "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin"
cmp "$OUT/metadata.json" "$OUT/metadata-extracted.json"
python3 - "$OUT/metadata-extracted.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["compat_version"] == "1.0" and "hiveton,h5000m" in data["supported_devices"]
assert data["version"]["target"] == "mediatek/filogic"
print("PASS: H5000M upgrade metadata round-trip verified")
PY

mkdir -p "$OUT/final-tar"
tar -xf "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin" -C "$OUT/final-tar"
final_root="$(find "$OUT/final-tar" -type f -name root -print -quit)"
unsquashfs -no-progress -d "$OUT/final-root" "$final_root" >/dev/null
grep -q 'higoos-login-wallpaper\.' "$OUT/final-root/usr/share/higoros/web/assets/"LoginPage-*.js
python3 - "$OUT/final-root" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
assets = root / "usr/share/higoros/web/assets"
plugins = next(assets.glob("PluginsPage-*.js")).read_text(encoding="utf-8")
router = next(path.read_text(encoding="utf-8") for path in assets.glob("index-*.js") if 'path:"apps/openclash"' in path.read_text(encoding="utf-8"))
assert 'to:{path:"/apps/openclash-luci"}' in plugins
assert 'path:"apps/openclash"' in router
assert 'path:"apps/openclash-luci"' in router
assert 'to:{path:"/apps/passwall-luci"}' in plugins and 'path:"apps/passwall-luci"' in router
assert 'cbi(appname .. "/client/global")' in (root / "usr/lib/lua/luci/controller/passwall.lua").read_text(encoding="utf-8")
assert (root / "usr/lib/lua/luci/model/cbi/passwall/client/global.lua").is_file()
assert len(list(assets.glob("higoos-native-openclash-*.js"))) == 1
assert (root / "www/cgi-bin/luci").is_file()
assert (root / "www/luci-static/resources/openclash").is_dir()
assert 'entry({"admin", "services", "openclash"}' in (root / "usr/lib/lua/luci/controller/openclash.lua").read_text(encoding="utf-8")
print("PASS: final firmware includes native LuCI OpenClash and PassWall and their embedded HigoOS entries")
PY
python3 - "$OUT/final-root/etc/config/openclash" "$OUT/final-root/etc/openclash/config" "$OUT/final-root/usr/share/higoros/web/assets" "$OUT/final-root/usr/share/openclash" <<'PY'
from pathlib import Path
import re
import sys
import yaml
uci = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"(?m)^\s*option config_path ['\"]([^'\"]+)['\"]", uci)
assert match, "OpenClash selected config_path is missing"
profile = yaml.safe_load((Path(sys.argv[2]) / Path(match.group(1)).name).read_text(encoding="utf-8"))
assert profile.get("proxies") == [] and profile.get("proxy-groups") == [] and profile.get("rules") == ["MATCH,DIRECT"]
configs = Path(sys.argv[2])
assert not (configs / "dy.yaml").exists() and not (configs / "127.0.0.1.yaml").exists()
openclash = next(Path(sys.argv[3]).glob("OpenClashPage-*.js")).read_text(encoding="utf-8")
assert len(openclash) > 1000 and 'y("iframe"' not in openclash
assert all(value in openclash for value in ("一键测速", "h5000mRunAllLatency", "Math.min(5,h5000mNodes.length)", "h5000mBulkProgress", '"test-latency",name', 'de.value[String(result.name)]'))
assert all(value in openclash for value in ("h5000mConfirmProxySelection", 'includes("节点选择回读不一致")', 'selected?.now===name'))
assert all(value in openclash for value in ('操作类型：', '配置文件 (.yaml)', '代理文件', '规则集文件', '[Meta] 内核文件 (.tar.gz)', '备份文件 (.tar.gz)', '选择文件', '未选择文件', '上传', '备份', 'onClick:downloadBackup', 'Ql={class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto"}'))
assert '"aria-label":"上传文件类型"' in openclash and '"aria-label":"操作类型"' not in openclash
assert '上传文件类型：' in openclash and 'aria-label":"新建文件类型"' in openclash and 'style:{display:uploadType.value==="create-file"?"":"none"}' in openclash
assert 'value:"create-file"},"新建文件"' in openclash
assert all(value not in openclash for value in ('value:"backup-download"', 'value:"create-config"', 'value:"create-overwrite"', 'value:"create-proxy-provider"', 'value:"create-rule-provider"', 'value:"create-custom"'))
assert 'class:"flex w-full flex-nowrap items-center gap-1 overflow-x-auto",style:' not in openclash
assert '配置文件保存在配置目录（/etc/openclash/config）' not in openclash
subscribe = (Path(sys.argv[4]) / "openclash.sh").read_text(encoding="utf-8")
core_update = (Path(sys.argv[4]) / "openclash_core.sh").read_text(encoding="utf-8")
assert 'ensure_meta_core_compat_link || {' in subscribe
assert 'ln -s "$TARGET_CORE_PATH" /etc/openclash/clash' in core_update
PY
sha256sum "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin" | tee "$OUT/SHA256SUMS.txt"
stat -c 'SIZE_BYTES=%s' "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin" | tee "$OUT/firmware-size.txt"
echo "PASS: complete H5000M repair features retained; original HigoOS OpenClash page and filtered backup import verified; requested profiles removed; upgrade metadata verified" | tee "$OUT/firmware-verification.txt"
