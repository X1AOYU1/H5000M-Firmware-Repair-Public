from pathlib import Path
import subprocess
import sys
import tempfile


repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    share = root / "usr/share/openclash"
    share.mkdir(parents=True)
    openclash = share / "openclash.sh"
    openclash.write_text(
        'CLASH="/etc/openclash/clash"\n'
        'config_test()\n{\n   if [ -f "$CLASH" ]; then\n      :\n   fi\n}\n',
        encoding="utf-8",
    )
    core_update = share / "openclash_core.sh"
    core_update.write_text(
        '                  UPDATE_SUCCESS=1\n                  restart=1\n',
        encoding="utf-8",
    )
    patcher = repo / "scripts/patch-openclash-meta-core-link.py"
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    patched_openclash = openclash.read_text(encoding="utf-8")
    patched_update = core_update.read_text(encoding="utf-8")
    required_openclash = (
        'meta_core_path="/etc/openclash/core/clash_meta"',
        'meta_core_path="/tmp/etc/openclash/core/clash_meta"',
        'ensure_meta_core_compat_link || {',
        'ln -s "$meta_core_path" "$CLASH"',
    )
    if not all(value in patched_openclash for value in required_openclash):
        raise SystemExit("ERROR: subscription path does not repair the missing Meta core link")
    if 'ln -s "$TARGET_CORE_PATH" /etc/openclash/clash' not in patched_update:
        raise SystemExit("ERROR: core update does not restore the canonical compatibility link")
    subprocess.run([sys.executable, str(patcher), str(root)], check=True)
    if openclash.read_text(encoding="utf-8") != patched_openclash:
        raise SystemExit("ERROR: OpenClash path patch is not idempotent")
    if core_update.read_text(encoding="utf-8") != patched_update:
        raise SystemExit("ERROR: core update patch is not idempotent")
print("PASS: Meta core compatibility link is repaired for subscription checks and core updates")
