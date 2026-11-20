#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile
import json


repo = Path(__file__).resolve().parents[1]
patcher = repo / "scripts/patch-higoros-openclash-entry.py"

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    asset = assets / "PluginsPage-fixture.js"
    asset.write_text(
        'const target={to:t.entryRoute||{path:"/other",query:{tab:t.featureKey}}};',
        encoding="utf-8",
    )

    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    source = asset.read_text(encoding="utf-8")
    expression = (
        'String(t.featureKey||t.name||"").toLowerCase()'
        '.replace(/^luci-app-/,"")==="openclash"?'
        '{path:"/apps/openclash"}:t.entryRoute||'
        '{path:"/other",query:{tab:t.featureKey}}'
    )
    expected = f"to:({expression})"
    if expected not in source:
        raise SystemExit("ERROR: OpenClash card route mapping was not emitted")

    js = f"""
      const routeFor = new Function('t', 'return (' + {json.dumps(expression)} + ')');
      const cases = [
        [{{featureKey:'openclash'}}, '/apps/openclash'],
        [{{featureKey:'luci-app-openclash',entryRoute:{{path:'/wrong'}}}}, '/apps/openclash'],
        [{{featureKey:'passwall'}}, '/other']
      ];
      for (const [app, expected] of cases) {{
        const route = routeFor(app);
        const actual = typeof route === 'string' ? route : route.path;
        if (actual !== expected) throw new Error(`${{app.featureKey}} routed to ${{actual}}`);
      }}
      console.log('PASS: dynamic app-card route selection sends OpenClash to /apps/openclash and preserves other app fallback');
    """
    subprocess.run(["node", "-e", js], check=True)
