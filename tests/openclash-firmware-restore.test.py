#!/usr/bin/env python3
"""Exercise the image's restore routine with its own ARM64 tar implementation."""
import io
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile


root = Path(sys.argv[1]).resolve(strict=True)
source = (root / "usr/lib/lua/luci/openclash.lua").read_text(encoding="utf-8")
restore = source[source.index("function restore_backup(archive)"):source.index("\nfunction get_age_keys")]
fixture = {
    "openclash": b"config openclash 'config'\n\toption config_path '/etc/openclash/config/dy.yaml'\n",
    "config/dy.yaml": b"proxies: []\nproxy-groups: []\nrules: [MATCH,DIRECT]\n",
    "config/127.0.0.1.yaml": b"proxies: []\nproxy-groups: []\nrules: [MATCH,REJECT]\n",
    "custom/test.list": b"DOMAIN,example.invalid\n",
    "rule_provider/test.yaml": b"payload: []\n",
    "core/clash_meta": b"incompatible core",
}
with tempfile.TemporaryDirectory(prefix="h5000m-restore-") as temp:
    base = Path(temp)
    busybox = shlex.join(["qemu-aarch64-static", "-L", str(root), str(root / "bin/busybox"), "tar"])
    setup = r'''
local base, tar = arg[2], arg[3]
local UTIL = { shellquote = function(s) return "'" .. s:gsub("'", "'\\''") .. "'" end }
local function sandbox(command)
    command = command:gsub("/etc/openclash", base .. "/etc/openclash")
    command = command:gsub("/etc/config/openclash", base .. "/etc/config/openclash")
    command = command:gsub("/tmp/oc_restore", base .. "/oc_restore")
    return command:gsub("^tar ", tar .. " ")
end
local SYS = {}
function SYS.call(command)
    if command:match("^uci set ") then
        local config = command:match("^uci set openclash%.config%.config_path=(.*)$")
        if config then
            local selected = assert(io.open(base .. "/selected", "w"))
            selected:write(config)
            selected:close()
        end
        return 0
    end
    assert(not command:find("/etc/init.d", 1, true))
    return os.execute(sandbox(command))
end
function SYS.exec(command)
    local fp = assert(io.popen(sandbox(command)))
    local out = fp:read("*a")
    fp:close()
    return out
end
'''
    restore = re.sub(r'"(/tmp/oc_restore[^" ]*)"', lambda m: f'base .. "{m[1][4:]}"', restore)
    test = base / "restore.lua"
    test.write_text(setup + restore + r'''
local ok, reason, names = restore_backup(arg[1])
if arg[4] == "fail" then
    assert(not ok and not names, "incomplete install reported success")
else
    assert(ok, tostring(reason))
    assert(#names == 2, "expected two installed profiles")
end
''', encoding="utf-8")
    for extension, mode in (("tar", "w"), ("tar.gz", "w:gz")):
        case = base / extension
        (case / "etc/config").mkdir(parents=True)
        config = case / "etc/openclash/config"
        config.mkdir(parents=True)
        (config / "config.yaml").write_bytes(b"rules: [MATCH,DIRECT]\n")
        backup = case / ("Backup-OpenClash-Hiveton H5000M." + extension)
        with tarfile.open(backup, mode, format=tarfile.USTAR_FORMAT) as archive:
            for name, contents in fixture.items():
                member = tarfile.TarInfo("./" + name)
                member.size = len(contents)
                archive.addfile(member, io.BytesIO(contents))
            link = tarfile.TarInfo("./clash")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/openclash/core/clash_meta"
            archive.addfile(link)
        subprocess.run(["lua5.1", str(test), str(backup), str(case), busybox], check=True)
        assert {path.name for path in config.glob("*.yaml")} == {"config.yaml", "dy.yaml", "127.0.0.1.yaml"}
        for name, contents in fixture.items():
            if name.startswith(("config/", "custom/", "rule_provider/")):
                assert (case / "etc/openclash" / name).read_bytes() == contents
        assert "dy.yaml" in (case / "selected").read_text(encoding="utf-8")
        assert not (case / "etc/openclash/core/clash_meta").exists()
        (config / "127.0.0.1.yaml").unlink()
        (config / "127.0.0.1.yaml").mkdir()
        subprocess.run(["lua5.1", str(test), str(backup), str(case), busybox, "fail"], check=True)
        print(f"PASS: packed ARM64 BusyBox restored both YAML profiles from .{extension}; a failed write cannot report success")
