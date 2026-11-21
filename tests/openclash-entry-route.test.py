#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
patcher = repo / "scripts/patch-higoros-openclash-entry.py"

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    asset = assets / "PluginsPage-fixture.js"
    expression = (
        '[t.featureKey,t.name,t.displayName,t.entryRoute?.path]'
        '.some(v=>String(v||"").toLowerCase().includes("openclash"))'
    )
    fallback = 't.entryRoute||{path:"/other",query:{tab:t.featureKey}}'
    for to in (fallback, f'({expression}?{{path:"/apps/openclash"}}:{fallback})'):
        asset.write_text(
            'const s=()=>{},r=(tag,props)=>[tag,props.href],ue=()=>"",me="",'
            'c=fn=>fn,x=()=>{},u=null,k=(_,props)=>["router-link",props.to.path];'
            f'const card=t=>t.kind==="native"?(s(),k(u,{{key:0,to:{to}}})):["legacy","existing"];',
            encoding="utf-8",
        )
        subprocess.run([sys.executable, str(patcher), str(root)], check=True)
        patched = asset.read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(patcher), str(root)], check=True)
        assert asset.read_text(encoding="utf-8") == patched
        subprocess.run(
            ["node", "-e", patched + """
                const expectedNative = ["router-link", "/apps/openclash-luci"];
                const cases = [
                  [{kind:"native",featureKey:"openclash"}, expectedNative],
                  [{kind:"native",name:"luci-app-openclash",entryRoute:{path:"/wrong"}}, expectedNative],
                  [{kind:"legacy",displayName:"OpenClash"}, expectedNative],
                  [{kind:"native",entryRoute:{path:"/apps/openclash"}}, expectedNative],
                  [{kind:"native",featureKey:"other"}, ["router-link", "/other"]],
                  [{kind:"native",entryRoute:{path:"/vpn"}}, ["router-link", "/vpn"]],
                  [{kind:"legacy",name:"other"}, ["legacy", "existing"]]
                ];
                for (const [app, expected] of cases) {
                  require("node:assert/strict").deepEqual(card(app), expected);
                }
            """],
            check=True,
        )
