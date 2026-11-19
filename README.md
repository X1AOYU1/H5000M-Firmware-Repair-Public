# H5000M complete-repair, node-free firmware

This repository rebuilds the complete repaired H5000M firmware from an encrypted baseline. The baseline is decrypted only on the ephemeral GitHub Actions runner. It is not committed in plaintext.

The build preserves the repaired WAN and IPv6 selectors, password policy controls, LuCI appearance and wallpaper fixes, package-market UI, and the other firmware contents. It removes only proxy nodes and subscription providers from the OpenClash profiles, retaining profile groups, rules, and non-secret resources. OpenClash remains disabled by default.

The build verifies the source profile shape, confirms that proxy nodes and credentials are absent from the public image, checks the retained firmware UI fixes, and round-trips the H5000M sysupgrade metadata.

Automated checks do not replace flashing and testing on an H5000M device.
