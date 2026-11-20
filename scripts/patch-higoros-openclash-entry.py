#!/usr/bin/env python3
"""Route the OpenClash app-center card to its HigoOS page."""
from pathlib import Path
import sys


def patch(root: Path) -> str:
    assets = root / "usr/share/higoros/web/assets"
    pages = sorted(assets.glob("PluginsPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one PluginsPage asset, found {len(pages)}")

    page = pages[0]
    source = page.read_text(encoding="utf-8")
    fallback = 'to:t.entryRoute||{path:"/other",query:{tab:t.featureKey}}'
    mapping = 'to:([t.featureKey,t.name,t.displayName,t.entryRoute?.path].some(v=>String(v||"").toLowerCase().includes("openclash"))?{path:"/apps/openclash"}:t.entryRoute||{path:"/other",query:{tab:t.featureKey}})'

    if mapping in source:
        return "PASS: OpenClash app card already maps to /apps/openclash"
    if source.count(fallback) != 1:
        raise SystemExit(
            "ERROR: expected one native app-card route fallback; "
            f"found {source.count(fallback)}"
        )

    page.write_text(source.replace(fallback, mapping, 1), encoding="utf-8")
    return "PASS: OpenClash app card now routes to /apps/openclash even when entryRoute is missing or stale"


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    if root is None:
        raise SystemExit("usage: patch-higoros-openclash-entry.py ROOTFS_DIR")
    print(patch(root))
