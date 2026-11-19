# H5000M complete-repair, node-free firmware

This repository rebuilds the complete repaired H5000M firmware from an encrypted baseline. The baseline is decrypted only on the ephemeral GitHub Actions runner. It is not committed in plaintext.

The build preserves the repaired WAN and IPv6 selectors, password policy controls, LuCI appearance and wallpaper fixes, package-market UI, and the other firmware contents. It removes the private `dy.yaml` and `127.0.0.1.yaml` OpenClash profiles and their backups, then leaves an empty starter profile with OpenClash disabled by default.

The HigoOS OpenClash page embeds the native LuCI interface in an isolated frame within the HigoOS layout. The login page displays Argon wallpaper uploads as a full-page image. The build checks both integrations, confirms private profiles and backup files are absent, checks the retained firmware UI fixes, and round-trips the H5000M sysupgrade metadata.

Automated checks do not replace flashing and testing on an H5000M device.
