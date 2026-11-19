#!/usr/bin/env python3
"""Give modified HigoOS web assets new URLs so clients cannot retain stale bundles."""
import hashlib
from pathlib import Path
import sys


TEXT_SUFFIXES = {".js", ".css", ".html", ".json", ".webmanifest"}


def revise(web_root: Path) -> str:
    asset_dir = web_root / "assets"
    pages = sorted(asset_dir.glob("SecurityPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one password page asset, found {len(pages)}")
    index = web_root / "index.html"
    if not index.is_file():
        raise SystemExit("ERROR: HigoOS web entry index.html is missing")

    assets = sorted((*asset_dir.glob("*.js"), *asset_dir.glob("*.css")))
    if not assets:
        raise SystemExit("ERROR: HigoOS web assets are missing")
    # The password page used to be the only revision input.  Consequently a
    # WAN-only fix kept the same asset URLs and installed browsers could keep
    # executing their cached NetworkPage bundle after a firmware upgrade.
    # Hash the complete asset set so every patched bundle changes all URLs.
    digest = hashlib.sha256()
    for path in assets:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    revision = digest.hexdigest()[:12]
    tag = f"-h5000m{revision}"
    mapping = {path.name: f"{path.stem}{tag}{path.suffix}" for path in assets}
    if len(set(mapping.values())) != len(mapping):
        raise SystemExit("ERROR: web asset revision names collide")
    if any((asset_dir / new_name).exists() for new_name in mapping.values()):
        raise SystemExit("ERROR: revised web asset name already exists")

    old_to_new = {old.encode(): new.encode() for old, new in mapping.items()}
    for path in web_root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        content = path.read_bytes()
        updated = content
        for old_name, new_name in old_to_new.items():
            updated = updated.replace(old_name, new_name)
        if updated != content:
            path.write_bytes(updated)

    for path in assets:
        path.rename(asset_dir / mapping[path.name])

    for path in web_root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        content = path.read_bytes()
        for old_name in old_to_new:
            if old_name in content:
                raise SystemExit(f"ERROR: stale web asset reference remains in {path.relative_to(web_root)}")

    for name in mapping.values():
        if not (asset_dir / name).is_file():
            raise SystemExit(f"ERROR: revised web asset is missing: {name}")
    return f"PASS: revisioned {len(assets)} HigoOS JS/CSS URLs with tag {tag}; entry and imports updated"


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    if root is None:
        raise SystemExit("usage: revision-higoros-web-assets.py ROOTFS_DIR")
    print(revise(root / "usr/share/higoros/web"))
