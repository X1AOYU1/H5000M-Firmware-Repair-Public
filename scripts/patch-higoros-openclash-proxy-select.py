#!/usr/bin/env python3
"""Retry and confirm OpenClash proxy selections when the control API lags."""
from pathlib import Path
import sys


HELPER = '''async function h5000mConfirmProxySelection(group,name){for(let attempt=0;attempt<4;attempt++){if(attempt)await new Promise(resolve=>setTimeout(resolve,250));const runtime=await $.engine("proxies"),proxies=runtime.proxies||{},selected=proxies[group];H.value=proxies;if(selected?.now===name)return!0}return!1}'''
OLD = '''async function Ge(a,e){if(!(t.value||j.value||c.value||w.value)){t.value=!0;try{await G(await $.select(a,e)),await N()}catch(l){U(l)}finally{t.value=!1}}}'''
NEW = '''async function Ge(a,e){if(!(t.value||j.value||c.value||w.value)){t.value=!0;try{await G(await $.select(a,e)),await N()}catch(error){if(String(error?.message||error).includes("节点选择回读不一致")){try{if(await h5000mConfirmProxySelection(a,e)){V.value="节点已切换";return}await G(await $.select(a,e));if(await h5000mConfirmProxySelection(a,e)){V.value="节点已切换";return}}catch(retryError){error=retryError}}U(error)}finally{t.value=!1}}}'''


def patch(root: Path) -> str:
    assets = root / "usr/share/higoros/web/assets"
    pages = sorted(assets.glob("OpenClashPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one OpenClashPage asset, found {len(pages)}")
    path = pages[0]
    source = path.read_text(encoding="utf-8")
    if "h5000mConfirmProxySelection" in source:
        if source.count("async function h5000mConfirmProxySelection(") != 1 or source.count("async function Ge(a,e)") != 1:
            raise SystemExit("ERROR: partial or duplicate proxy-selection recovery patch detected")
        return "PASS: OpenClash proxy selection already retries and confirms delayed readback"
    if source.count(OLD) != 1:
        raise SystemExit("ERROR: expected one OpenClash proxy-selection handler")
    source = source.replace(OLD, HELPER + NEW, 1)
    if source.count("async function h5000mConfirmProxySelection(") != 1:
        raise SystemExit("ERROR: proxy-selection confirmation helper was not installed")
    path.write_text(source, encoding="utf-8")
    return "PASS: OpenClash proxy selection now retries once after readback mismatch and verifies the actual selected node"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-openclash-proxy-select.py ROOTFS_DIR")
    print(patch(Path(sys.argv[1])))
