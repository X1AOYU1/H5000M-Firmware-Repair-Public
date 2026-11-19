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

python3 - "$OUT/rootfs" <<'PY'
from pathlib import Path
import re
import sys
import yaml

root = Path(sys.argv[1])
oc = root / "etc/openclash"
config_dir = oc / "config"
config_dir.mkdir(parents=True, exist_ok=True)
profiles = sorted({*oc.rglob("*.yaml"), *oc.rglob("*.yml")})
config_profiles = [path for path in profiles if path.is_relative_to(config_dir)]
if not config_profiles:
    raise SystemExit("ERROR: no OpenClash YAML profiles found to sanitize")
selected_profile = next((path for path in config_profiles if path.name == "dy.yaml"), config_profiles[0])
source_profile = yaml.safe_load(selected_profile.read_text(encoding="utf-8"))
if not isinstance(source_profile, dict) or len(source_profile.get("proxies", [])) != 176:
    raise SystemExit("ERROR: expected the selected 176-node dy.yaml source profile")
if len(source_profile.get("proxy-groups", [])) != 5 or len(source_profile.get("rules", [])) != 24:
    raise SystemExit("ERROR: selected dy.yaml configuration shape does not match the verified source")
for path in profiles:
    if not (path.is_relative_to(config_dir) or path.is_relative_to(oc / "backup")):
        continue
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid OpenClash profile: {path.relative_to(root)}")
    data["proxies"] = []
    data.pop("proxy-providers", None)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

for path in (oc / "custom", oc / "overwrite", oc / "rule_provider"):
    if not path.is_dir():
        continue
    for item in path.rglob("*"):
        if item.is_file():
            try:
                text = item.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if re.search(r"(?i)(?:password|passwd|secret|token|uuid)\s*[:=]\s*[^\s,'\"]+|(?:vmess|vless|trojan|ss)://", text):
                raise SystemExit(f"ERROR: credential-bearing OpenClash resource found: {item.relative_to(root)}")

uci = root / "etc/config/openclash"
if not uci.is_file():
    raise SystemExit("ERROR: OpenClash UCI configuration missing")
text = uci.read_text(encoding="utf-8")
secret_keys = re.compile(r"(?i)(?:subscribe|subscription|token|password|passwd|secret|uuid|server_url|config_url|repo_url|github|access_key|refresh_token)")
lines = [line for line in text.splitlines() if not (line.lstrip().startswith(("option ", "list ")) and secret_keys.search(line.split(None, 2)[1] if len(line.split(None, 2)) > 1 else ""))]
text = "\n".join(lines) + "\n"
section_start = re.search(r"(?m)^config\s+openclash\s+['\"]config['\"]\s*$", text)
if not section_start:
    raise SystemExit("ERROR: OpenClash config UCI section missing")
next_section = re.search(r"(?m)^config\s+", text[section_start.end():])
section_end = section_start.end() + next_section.start() if next_section else len(text)
section = text[section_start.start():section_end]
for key, value in {"enable": "0", "config_path": "/" + str(selected_profile.relative_to(root))}.items():
    pattern = re.compile(rf"(?m)^[ \t]*option[ \t]+{re.escape(key)}[ \t]+['\"][^'\"]*['\"][ \t]*$")
    rendered = f"\toption {key} '{value}'"
    section = pattern.sub(rendered, section, count=1) if pattern.search(section) else section.rstrip() + "\n" + rendered + "\n"
text = text[:section_start.start()] + section + text[section_end:]
uci.write_text(text, encoding="utf-8")

print("PASS: removed proxy nodes from profiles and sanitized profile UCI while preserving groups and rules")
PY

# Apply the current login-page fix and revise every SPA asset URL afterward.
python3 scripts/patch-higoros-login-wallpaper.py "$OUT/rootfs" | tee "$OUT/login-wallpaper-fix.txt"
python3 scripts/patch-higoros-openclash-luci-link.py "$OUT/rootfs" | tee "$OUT/openclash-luci-link.txt"
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
package = next((assets.glob("PackagesPage-*.js")), None)
checks = {
    "login wallpaper": "higoos-login-wallpaper." in login and "wallpaper.value?{backgroundImage:" in login,
    "wallpaper upload cache reset": 'localStorage.removeItem("higoos_argon_login_wallpaper_source")' in native,
    "Argon upload publication": 'new File([blob],aliasName' in native,
    "native LuCI OpenClash link": 'href:"/cgi-bin/luci/admin/services/openclash"' in next(assets.glob("OpenClashPage-*.js")).read_text(encoding="utf-8"),
    "WAN and IPv6 edit controls": all(value in network for value in ('key:"dhcp"', 'key:"static"', 'key:"pppoe"', 'key:"ds-lite"', "ipv6Types", "saveWANConfig", "saveIPv6Config")),
    "password policy controls": all(value in security for value in ("requireNumber", "requireLowercase", "requireUppercase", "requireSpecialChar", "密码策略已保存")),
    "appearance settings UI": package is not None and "LuCI" in package.read_text(encoding="utf-8"),
    "package market UI": package is not None,
}
for label, passed in checks.items():
    if not passed:
        raise SystemExit(f"ERROR: complete-repair feature missing after node cleanup: {label}")
    print(f"PASS: retained complete-repair feature: {label}")

oc = root / "etc/openclash"
profile = yaml.safe_load((oc / "config/dy.yaml").read_text(encoding="utf-8"))
if profile.get("proxies") != [] or not profile.get("proxy-groups") or not profile.get("rules"):
    raise SystemExit("ERROR: sanitized profile lost proxy-group or rule settings")
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
        if isinstance(data, dict) and data.get("proxies"):
            raise SystemExit(f"ERROR: proxy nodes remain in {path.relative_to(root)}")
print("PASS: OpenClash profile nodes and UCI subscription credentials are absent; groups and rules remain")
PY

login_asset="$(find "$OUT/rootfs/usr/share/higoros/web/assets" -maxdepth 1 -type f -name 'LoginPage-*.js' -print -quit)"
node --check "$login_asset"
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
python3 - "$OUT/final-root/etc/config/openclash" "$OUT/final-root/etc/openclash/config" <<'PY'
from pathlib import Path
import re
import sys
import yaml
uci = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"(?m)^\s*option config_path ['\"]([^'\"]+)['\"]", uci)
assert match, "OpenClash selected config_path is missing"
profile = yaml.safe_load((Path(sys.argv[2]) / Path(match.group(1)).name).read_text(encoding="utf-8"))
assert profile.get("proxies") == [] and profile.get("proxy-groups") and profile.get("rules")
PY
sha256sum "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin" | tee "$OUT/SHA256SUMS.txt"
stat -c 'SIZE_BYTES=%s' "$OUT/H5000M-6.6.160-full-repair-NO-NODES.bin" | tee "$OUT/firmware-size.txt"
echo "PASS: complete H5000M repair features retained; OpenClash nodes removed; upgrade metadata verified" | tee "$OUT/firmware-verification.txt"
