#!/usr/bin/env python3
"""Make OpenClash subscription checks resolve the installed Meta core."""
from pathlib import Path
import sys


root = Path(sys.argv[1]).resolve()
openclash = root / "usr/share/openclash/openclash.sh"
core_update = root / "usr/share/openclash/openclash_core.sh"
if not openclash.is_file() or not core_update.is_file():
    raise SystemExit("ERROR: OpenClash core scripts are missing")

source = openclash.read_text(encoding="utf-8")
helper = '''ensure_meta_core_compat_link()
{
   [ -x "$CLASH" ] && return 0
   local meta_core_path
   if [ "$(uci_get_config \"small_flash_memory\")" = "1" ]; then
      meta_core_path="/tmp/etc/openclash/core/clash_meta"
   else
      meta_core_path="/etc/openclash/core/clash_meta"
   fi
   [ -x "$meta_core_path" ] || return 1
   rm -f "$CLASH"
   ln -s "$meta_core_path" "$CLASH" || return 1
   [ -x "$CLASH" ]
}

'''
if "ensure_meta_core_compat_link()" not in source:
    anchor = "config_test()\n{\n"
    if anchor not in source:
        raise SystemExit("ERROR: OpenClash config-test anchor changed")
    source = source.replace(anchor, helper + anchor, 1)
if 'ensure_meta_core_compat_link || {' not in source:
    anchor = 'config_test()\n{\n   if [ -f "$CLASH" ]; then'
    replacement = 'config_test()\n{\n   ensure_meta_core_compat_link || {\n      LOG_ERROR "Meta core binary not found: $CLASH (expected ARM64 Meta core under /etc/openclash/core)"\n      return 1\n   }\n   if [ -f "$CLASH" ]; then'
    if anchor not in source:
        raise SystemExit("ERROR: OpenClash config-test invocation anchor changed")
    source = source.replace(anchor, replacement, 1)
openclash.write_text(source, encoding="utf-8")

source = core_update.read_text(encoding="utf-8")
anchor = '''                  UPDATE_SUCCESS=1
                  restart=1'''
replacement = '''                  if [ -x "$TARGET_CORE_PATH" ]; then
                     rm -f /etc/openclash/clash
                     ln -s "$TARGET_CORE_PATH" /etc/openclash/clash || {
                        LOG_ERROR "Meta core installed but compatibility link could not be created"
                        break
                     }
                  fi
                  UPDATE_SUCCESS=1
                  restart=1'''
if anchor in source and 'Meta core installed but compatibility link could not be created' not in source:
    source = source.replace(anchor, replacement, 1)
elif 'Meta core installed but compatibility link could not be created' not in source:
    raise SystemExit("ERROR: OpenClash core-update success anchor changed")
core_update.write_text(source, encoding="utf-8")
print("PASS: OpenClash subscription and core updates restore the canonical /etc/openclash/clash link to the selected Meta core")
