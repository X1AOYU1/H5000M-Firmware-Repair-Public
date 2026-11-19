# H5000M node-free firmware repair

This public repository builds a H5000M image from a baseline that contains no user proxy nodes. The build verifies the empty OpenClash proxy lists before and after repacking and publishes only the firmware and checksums.

The OpenClash service remains disabled by default. Firmware artifacts from this repository contain no private subscription profile, nodes, or backup archive.

The current repair makes uploaded Argon image backgrounds available on the HigoOS login page. After uploading an image in the authenticated settings UI, the page publishes a stable local copy for the unauthenticated login screen. Missing images fall back to the original login appearance.

GitHub Actions build on `ubuntu-24.04`, using a standard GitHub-hosted runner and a public, node-free baseline release asset.

Automated checks do not replace flashing and testing on an H5000M device.
