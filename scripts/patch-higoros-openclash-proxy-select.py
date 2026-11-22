#!/usr/bin/env python3
"""Distinguish active and preferred nodes when OpenClash reports a mismatch."""
from pathlib import Path
import sys


HELPER = '''async function h5000mConfirmProxySelection(group,name){let selected;for(let attempt=0;attempt<4;attempt++){if(attempt)await new Promise(resolve=>setTimeout(resolve,250));const runtime=await $.engine("proxies"),proxies=runtime.proxies||{};selected=proxies[group];H.value=proxies;if(selected?.now===name)return{active:!0,preferred:!0}}return{active:!1,preferred:selected?.fixed===name}}'''
OLD = '''async function Ge(a,e){if(!(t.value||j.value||c.value||w.value)){t.value=!0;try{await G(await $.select(a,e)),await N()}catch(l){U(l)}finally{t.value=!1}}}'''
NEW = '''async function Ge(a,e){if(t.value||j.value||c.value||w.value||!v.value?.coreAvailable)return;const group=H.value[a];if(!group?.all?.includes(e))return;t.value=!0;try{const automatic=["URLTest","Fallback","Smart"].includes(group.type),attempts=group.type==="Selector"?2:1;for(let attempt=0;attempt<attempts;attempt++){let mismatch;try{await G(await $.select(a,e))}catch(error){if(!String(error?.message||error).includes("节点选择回读不一致"))throw error;mismatch=error}const result=await h5000mConfirmProxySelection(a,e);if(result.active){V.value="节点已切换";return}if(automatic){V.value=result.preferred?"已设为偏好节点，自动组目前仍使用其他节点":"自动组选中的节点未生效，仍显示当前节点。需要指定节点时，可用手动选择组。";return}if(attempt===attempts-1)throw mismatch||new Error("未确认节点切换，仍显示当前节点")}}catch(error){U(error)}finally{t.value=!1}}'''
OLD_CONTROL = 'value:u.now,disabled:t.value,class:"rounded border border-line-1/70 bg-bg-2/50 p-2",onChange:I=>Ge(l,I.target.value)'
NEW_CONTROL = 'value:u.now,disabled:t.value||j.value||!v.value?.coreAvailable,class:"rounded border border-line-1/70 bg-bg-2/50 p-2",onChange:I=>{const target=I.target,name=target.value;target.value=u.now??"";void Ge(l,name)}'


def patch(root: Path) -> str:
    assets = root / "usr/share/higoros/web/assets"
    pages = sorted(assets.glob("OpenClashPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one OpenClashPage asset, found {len(pages)}")
    path = pages[0]
    source = path.read_text(encoding="utf-8")
    if HELPER + NEW in source and NEW_CONTROL in source:
        return "PASS: OpenClash proxy selection already separates preferred and active nodes"
    if (source.count(OLD) != 1 or source.count(OLD_CONTROL) != 1
            or "h5000mConfirmProxySelection" in source):
        raise SystemExit("ERROR: expected one original OpenClash selection handler and dropdown")
    source = source.replace(OLD, HELPER + NEW, 1).replace(OLD_CONTROL, NEW_CONTROL, 1)
    path.write_text(source, encoding="utf-8")
    return "PASS: OpenClash distinguishes automatic preferences from active nodes and confirms manual selection"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-openclash-proxy-select.py ROOTFS_DIR")
    print(patch(Path(sys.argv[1])))
