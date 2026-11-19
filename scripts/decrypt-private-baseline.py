#!/usr/bin/env python3
"""Decrypt the private full-repair baseline inside GitHub Actions."""
import base64
from pathlib import Path
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


source, destination, encoded_key = sys.argv[1:]
payload = Path(source).read_bytes()
if len(payload) < 28:
    raise SystemExit("ERROR: encrypted baseline is truncated")
nonce, tag, ciphertext = payload[:12], payload[12:28], payload[28:]
key = base64.b64decode(encoded_key, validate=True)
plaintext = AESGCM(key).decrypt(nonce, ciphertext + tag, b"H5000M-public-baseline-v1")
Path(destination).write_bytes(plaintext)
print("PASS: decrypted private baseline in the ephemeral runner")
