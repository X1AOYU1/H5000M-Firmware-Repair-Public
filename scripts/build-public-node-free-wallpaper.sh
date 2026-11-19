#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:?usage: build-public-node-free-wallpaper.sh node-free-base.bin output-dir}"
OUT="${2:?missing output directory}"
EXPECTED="411c4f83208d62144d8556adc54bcb3bdd5291279cc34bec7095d32e3f851806"
mkdir -p "$OUT/tar" "$OUT/rootfs"
actual="$(sha256sum "$IMAGE" | awk '{print $1}')"
[[ "$actual" == "$EXPECTED" ]] || { echo "ERROR: node-free base firmware SHA256 mismatch"; exit 2; }
tar -xf "$IMAGE" -C "$OUT/tar"
root="$(find "$OUT/tar" -type f -name root -print -quit)"
[[ -n "$root" ]] || { echo "ERROR: firmware root SquashFS missing"; exit 3; }
unsquashfs -no-progress -d "$OUT/rootfs" "$root" >/dev/null

config="$OUT/rootfs/etc/openclash/config/config.yaml"
[[ -f "$config" ]] || { echo "ERROR: no-node OpenClash starter config missing"; exit 4; }
python3 - "$config" <<'PY'
from pathlib import Path
import sys
import yaml
path = Path(sys.argv[1])
config = yaml.safe_load(path.read_text(encoding="utf-8"))
if not isinstance(config, dict) or config.get("proxies") != [] or config.get("proxy-groups") != []:
    raise SystemExit("ERROR: public firmware base contains proxy nodes or groups")
if any(key in config for key in ("proxy-providers", "proxy-provider")):
    raise SystemExit("ERROR: public firmware base contains proxy providers")
print("PASS: OpenClash profile contains no nodes, groups, or providers")
PY
if find "$OUT/rootfs/etc/openclash" -type f \( -iname '*.yaml' -o -iname '*.yml' \) \
    -exec grep -IlE '^[[:space:]]*(server|password|uuid|token):[[:space:]]*[^[:space:]]+' {} + | grep -q .; then
  echo "ERROR: possible credential-bearing YAML found in public firmware base"
  exit 5
fi

python3 scripts/patch-higoros-login-wallpaper.py "$OUT/rootfs" | tee "$OUT/login-wallpaper-fix.txt"
python3 scripts/revision-higoros-web-assets.py "$OUT/rootfs" | tee "$OUT/frontend-asset-revision.txt"
node_asset="$(find "$OUT/rootfs/usr/share/higoros/web/assets" -maxdepth 1 -type f -name 'LoginPage-*.js' -print -quit)"
node --check "$node_asset"

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
cp "$OUT/repaired.tar" "$OUT/H5000M-6.6.160-login-wallpaper-NO-NODES.bin"

mkdir -p "$OUT/final-tar"
tar -xf "$OUT/H5000M-6.6.160-login-wallpaper-NO-NODES.bin" -C "$OUT/final-tar"
final_root="$(find "$OUT/final-tar" -type f -name root -print -quit)"
unsquashfs -no-progress -d "$OUT/final-root" "$final_root" >/dev/null
grep -q 'higoos-login-wallpaper\.' "$OUT/final-root/usr/share/higoros/web/assets/"LoginPage-*.js
grep -q 'new File(\[blob\],aliasName' "$OUT/final-root/usr/share/higoros/web/assets/"NativeConfigSection*.js
python3 - "$OUT/final-root/etc/openclash/config/config.yaml" <<'PY'
from pathlib import Path
import sys
import yaml
config = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
if config.get("proxies") != [] or config.get("proxy-groups") != []:
    raise SystemExit("ERROR: final firmware is not node-free")
PY
sha256sum "$OUT/H5000M-6.6.160-login-wallpaper-NO-NODES.bin" | tee "$OUT/SHA256SUMS.txt"
stat -c 'SIZE_BYTES=%s' "$OUT/H5000M-6.6.160-login-wallpaper-NO-NODES.bin" | tee "$OUT/firmware-size.txt"
echo "PASS: final firmware contains the login wallpaper fix and no proxy nodes" | tee "$OUT/firmware-verification.txt"
