#!/usr/bin/env python3
"""Open the embedded native OpenClash page from the HigoOS app center."""
from pathlib import Path
import sys

OPENCLASH = '[t.featureKey,t.name,t.displayName,t.entryRoute?.path].some(v=>String(v||"").toLowerCase().includes("openclash"))'
NATIVE = 't.kind==="native"?(s(),k(u,{key:0,'
FALLBACK = 'to:t.entryRoute||{path:"/other",query:{tab:t.featureKey}}'
OLD_MAPPING = f'to:({OPENCLASH}?{{path:"/apps/openclash"}}:t.entryRoute||{{path:"/other",query:{{tab:t.featureKey}}}})'
LUCI = '(s(),k(u,{key:3,to:{path:"/apps/openclash-luci"},class:ue(me)},{default:c(()=>[x("打开",-1)]),_:1},8,["to"]))'
PREVIOUS = '(s(),r("a",{key:3,href:"/cgi-bin/luci/admin/services/openclash",class:ue(me)},"打开",2))'
ENTRY = f'{OPENCLASH}?{LUCI}:'


def patch(root: Path) -> str:
    assets = root / "usr/share/higoros/web/assets"
    pages = sorted(assets.glob("PluginsPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one PluginsPage asset, found {len(pages)}")

    page = pages[0]
    source = page.read_text(encoding="utf-8")
    if ENTRY + NATIVE + FALLBACK in source:
        return "PASS: OpenClash app card already opens LuCI inside HigoOS"
    previous = f"{OPENCLASH}?{PREVIOUS}:{NATIVE}{FALLBACK}"
    if source.count(previous) == 1:
        page.write_text(source.replace(previous, ENTRY + NATIVE + FALLBACK, 1), encoding="utf-8")
        return "PASS: OpenClash app card now opens LuCI inside HigoOS"
    candidates = [NATIVE + props for props in (FALLBACK, OLD_MAPPING)]
    if sum(source.count(anchor) for anchor in candidates) != 1:
        raise SystemExit("ERROR: expected one native app-card link")
    anchor = next(anchor for anchor in candidates if anchor in source)
    page.write_text(source.replace(anchor, ENTRY + NATIVE + FALLBACK, 1), encoding="utf-8")
    return "PASS: OpenClash app card now opens LuCI inside HigoOS"


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    if root is None:
        raise SystemExit("usage: patch-higoros-openclash-entry.py ROOTFS_DIR")
    print(patch(root))
