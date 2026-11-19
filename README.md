# H5000M complete-repair, node-free firmware

This repository rebuilds the complete repaired H5000M firmware from an encrypted baseline. The baseline is decrypted only on the ephemeral GitHub Actions runner. It is not committed in plaintext.

The build preserves the repaired WAN and IPv6 selectors, password policy controls, LuCI appearance and wallpaper fixes, package-market UI, and the other firmware contents. It removes the private `dy.yaml` and `127.0.0.1.yaml` OpenClash profiles and their backups, then leaves an empty starter profile with OpenClash disabled by default.

The HigoOS OpenClash page is kept in its original interface and layout. Its configuration files view accepts OpenClash `.tar.gz` backups and restores profiles, custom scripts, overwrite files, providers, and route sets while skipping donor cores, Smart Model data, caches, and geo databases. The importer keeps OpenClash disabled, selects Meta, and maps the interface to `br-lan`. The login page displays Argon wallpaper uploads as a full-page image. The build checks the retained firmware UI fixes, confirms private profiles and backup files are absent, and round-trips the H5000M sysupgrade metadata.

Automated checks do not replace flashing and testing on an H5000M device.
