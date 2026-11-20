from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
patcher = repo / "scripts/patch-higoros-openclash-bulk-latency.py"

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    assets = root / "usr/share/higoros/web/assets"
    assets.mkdir(parents=True)
    asset = assets / "OpenClashPage-fixture.js"
    asset.write_text(
        'async function T(a,e,l,u){return a} '
        'f.value==="runtime"?(o(),y("section",Fl,['
        '(o(!0),y(E,null,O(Be.value,([l,u])=>l),128))',
        encoding="utf-8",
    )

    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    first = asset.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    second = asset.read_text(encoding="utf-8")
    if first != second:
        raise SystemExit("ERROR: OpenClash one-click latency patch is not idempotent")

    requirements = (
        'h5000mRunAllLatency(){',
        'h5000mNodes=Object.entries(H.value).filter(([,entry])=>!Array.isArray(entry.all))',
        'Math.min(5,h5000mNodes.length)',
        '$.action("test-latency",name)',
        '$.job(task.jobId)',
        'de.value[String(result.name)]=Number(result.delayMs)',
        'h5000mBulkProgress.value',
        '批量测速完成：成功',
        '一键测速',
        'h5000mRunAllLatency',
    )
    if not all(value in first for value in requirements):
        raise SystemExit("ERROR: bulk-latency UI or bounded worker behavior is incomplete")
    if first.count("h5000mRunAllLatency") != 2 or first.count("一键测速") != 1:
        raise SystemExit("ERROR: bulk-latency handler or control was duplicated")
    if '"test-latency",name' not in first or '.select(' in first:
        raise SystemExit("ERROR: bulk latency must test nodes without changing the selected proxy")

print("PASS: OpenClash one-click latency test uses bounded concurrency, reports progress, updates results, and preserves proxy selection")
