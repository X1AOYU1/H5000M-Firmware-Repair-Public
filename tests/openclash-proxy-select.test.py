from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
patcher = repo / "scripts/patch-higoros-openclash-proxy-select.py"
old = 'async function Ge(a,e){if(!(t.value||j.value||c.value||w.value)){t.value=!0;try{await G(await $.select(a,e)),await N()}catch(l){U(l)}finally{t.value=!1}}}'

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    page = assets / "OpenClashPage-fixture.js"
    page.write_text(
        'const t={value:!1},j={value:!1},c={value:!1},w={value:!1},v={value:{coreAvailable:!0}},'
        '$={select:async()=>({}),engine:async()=>({proxies:{}})},G=async()=>{},N=async()=>{},'
        'H={value:{group:{all:["node"],type:"Selector"}}},V={value:""},u={now:"node"},l="group";'
        'const control={value:u.now,disabled:t.value,class:"rounded border border-line-1/70 bg-bg-2/50 p-2",'
        'onChange:I=>Ge(l,I.target.value)};' + old,
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    first = page.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    if page.read_text(encoding="utf-8") != first:
        raise SystemExit("ERROR: proxy selection patch is not idempotent")
    required = (
        'includes("节点选择回读不一致")',
        'await G(await $.select(a,e))',
        'await h5000mConfirmProxySelection(a,e)',
        'selected?.now===name',
        'attempt<4',
        'setTimeout(resolve,250)',
        'V.value="节点已切换"',
    )
    if not all(value in first for value in required):
        raise SystemExit("ERROR: bounded proxy-selection recovery is incomplete")
    if 'group.type==="Selector"?2:1' not in first or 'target.value=u.now??""' not in first:
        raise SystemExit("ERROR: manual selection retry or failed-selection rollback is missing")
    node = shutil.which("node")
    if node:
        check = subprocess.run([node, "--check", str(page)], capture_output=True, text=True)
        if check.returncode:
            raise SystemExit(check.stderr or check.stdout)

print("PASS: proxy-selection recovery retries once, confirms actual core state, and keeps errors when selection is not confirmed")
