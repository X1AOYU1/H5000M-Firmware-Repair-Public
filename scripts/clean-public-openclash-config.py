#!/usr/bin/env python3
"""Remove private OpenClash profiles while preserving plugin resources."""
from pathlib import Path
import re
import shutil
import sys

import yaml


root = Path(sys.argv[1])
oc = root / "etc/openclash"
config_dir = oc / "config"
config_dir.mkdir(parents=True, exist_ok=True)
profiles = sorted({*oc.rglob("*.yaml"), *oc.rglob("*.yml")})
config_profiles = [path for path in profiles if path.is_relative_to(config_dir)]
source = next((path for path in config_profiles if path.name == "dy.yaml"), None)
if source is None:
    raise SystemExit("ERROR: expected the verified dy.yaml source profile")
data = yaml.safe_load(source.read_text(encoding="utf-8"))
if not isinstance(data, dict) or len(data.get("proxies", [])) != 176:
    raise SystemExit("ERROR: dy.yaml source profile does not match the verified input")
if len(data.get("proxy-groups", [])) != 5 or len(data.get("rules", [])) != 24:
    raise SystemExit("ERROR: dy.yaml source profile shape does not match the verified input")

# Sanitize any additional profiles that are retained, then remove the two
# uploaded user profiles and all backups before installing a clean placeholder.
for path in profiles:
    if not (path.is_relative_to(config_dir) or path.is_relative_to(oc / "backup")):
        continue
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise SystemExit(f"ERROR: invalid OpenClash profile: {path.relative_to(root)}")
    node_names = {item.get("name") for item in content.get("proxies", []) if isinstance(item, dict) and item.get("name")}
    content["proxies"] = []
    content.pop("proxy-providers", None)
    group_names = {item.get("name") for item in content.get("proxy-groups", []) if isinstance(item, dict) and item.get("name")}
    builtins = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "GLOBAL"}
    for group in content.get("proxy-groups", []):
        if not isinstance(group, dict):
            continue
        if isinstance(group.get("proxies"), list):
            group["proxies"] = [name for name in group["proxies"] if name not in node_names and (name in group_names or name in builtins)]
        group.pop("use", None)
    path.write_text(yaml.safe_dump(content, allow_unicode=True, sort_keys=False), encoding="utf-8")

for name in ("127.0.0.1.yaml", "dy.yaml"):
    (config_dir / name).unlink(missing_ok=True)
backup_dir = oc / "backup"
if backup_dir.exists():
    shutil.rmtree(backup_dir)
(config_dir / "config.yaml").write_text(
    "mixed-port: 7893\nallow-lan: false\nmode: rule\nlog-level: info\n"
    "proxies: []\nproxy-groups: []\nrules:\n  - MATCH,DIRECT\n",
    encoding="utf-8",
)

for path in (oc / "custom", oc / "overwrite", oc / "rule_provider"):
    if not path.is_dir():
        continue
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            text = item.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if re.search(r"(?i)(?:password|passwd|secret|token|uuid)\s*[:=]\s*[^\s,'\"]+|(?:vmess|vless|trojan|ss)://", text):
            raise SystemExit(f"ERROR: credential-bearing OpenClash resource found: {item.relative_to(root)}")

uci = root / "etc/config/openclash"
if not uci.is_file():
    raise SystemExit("ERROR: OpenClash UCI configuration missing")
text = uci.read_text(encoding="utf-8")
secret_keys = re.compile(r"(?i)(?:subscribe|subscription|config_update_path|token|password|passwd|secret|uuid|server_url|config_url|repo_url|github|access_key|refresh_token)")
lines = [line for line in text.splitlines() if not (line.lstrip().startswith(("option ", "list ")) and secret_keys.search(line.split(None, 2)[1] if len(line.split(None, 2)) > 1 else ""))]
text = "\n".join(lines) + "\n"
section_start = re.search(r"(?m)^config\s+openclash\s+['\"]config['\"]\s*$", text)
if not section_start:
    raise SystemExit("ERROR: OpenClash config UCI section missing")
next_section = re.search(r"(?m)^config\s+", text[section_start.end():])
section_end = section_start.end() + next_section.start() if next_section else len(text)
section = text[section_start.start():section_end]
for key, value in {"enable": "0", "config_path": "/etc/openclash/config/config.yaml"}.items():
    pattern = re.compile(rf"(?m)^[ \t]*option[ \t]+{re.escape(key)}[ \t]+['\"][^'\"]*['\"][ \t]*$")
    rendered = f"\toption {key} '{value}'"
    section = pattern.sub(rendered, section, count=1) if pattern.search(section) else section.rstrip() + "\n" + rendered + "\n"
text = text[:section_start.start()] + section + text[section_end:]
uci.write_text(text, encoding="utf-8")

if any((config_dir / name).exists() for name in ("127.0.0.1.yaml", "dy.yaml")):
    raise SystemExit("ERROR: requested OpenClash profiles were not removed")
print("PASS: deleted dy.yaml, 127.0.0.1.yaml, and OpenClash backups; installed an empty starter profile")
