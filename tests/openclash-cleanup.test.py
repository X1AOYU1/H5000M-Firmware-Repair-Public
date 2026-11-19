from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    oc = root / "etc/openclash"
    config = oc / "config"
    config.mkdir(parents=True)
    nodes = [{"name": f"proxy-{i}", "type": "ss", "server": "example.invalid", "port": 443, "cipher": "aes-128-gcm", "password": "private"} for i in range(176)]
    groups = [{"name": f"group-{i}", "type": "select", "proxies": ["DIRECT", *(node["name"] for node in nodes)]} for i in range(5)]
    rules = [f"MATCH,group-{i}" for i in range(24)]
    source = {"proxies": nodes, "proxy-groups": groups, "rules": rules}
    (config / "dy.yaml").write_text(yaml.safe_dump(source), encoding="utf-8")
    (config / "127.0.0.1.yaml").write_text(yaml.safe_dump({"proxies": nodes[:6], "proxy-groups": [], "rules": []}), encoding="utf-8")
    backup = oc / "backup"
    backup.mkdir()
    (backup / "old.yaml").write_text(yaml.safe_dump(source), encoding="utf-8")
    for name in ("custom", "overwrite", "rule_provider"):
        (oc / name).mkdir()
    uci = root / "etc/config/openclash"
    uci.parent.mkdir(parents=True)
    uci.write_text(
        "config openclash 'config'\n\toption enable '1'\n\toption config_path '/etc/openclash/config/dy.yaml'\n\toption config_update_path 'https://private.invalid/sub'\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, str(repo / "scripts/clean-public-openclash-config.py"), str(root)], check=True)
    assert not (config / "dy.yaml").exists()
    assert not (config / "127.0.0.1.yaml").exists()
    assert not backup.exists()
    clean = yaml.safe_load((config / "config.yaml").read_text(encoding="utf-8"))
    assert clean["proxies"] == [] and clean["proxy-groups"] == [] and clean["rules"] == ["MATCH,DIRECT"]
    cleaned_uci = uci.read_text(encoding="utf-8")
    assert "option enable '0'" in cleaned_uci
    assert "option config_path '/etc/openclash/config/config.yaml'" in cleaned_uci
    assert "private.invalid" not in cleaned_uci
print("PASS: requested OpenClash profiles and backup are deleted; empty profile remains disabled")
