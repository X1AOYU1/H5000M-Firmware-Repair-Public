#!/usr/bin/env python3
"""Encrypt a local baseline and seal its AES key to a GitHub Actions public key."""
import base64
import hashlib
import os
from pathlib import Path
import sys

from nacl.public import PublicKey, SealedBox
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

source, encrypted_path, github_public_key, sealed_key_path, secret_key_path = sys.argv[1:]
source_path = Path(source)
encrypted_output = Path(encrypted_path)
key = AESGCM.generate_key(bit_length=256)
nonce = os.urandom(12)
ciphertext = AESGCM(key).encrypt(nonce, source_path.read_bytes(), b"H5000M-public-baseline-v1")
encrypted_output.write_bytes(nonce + ciphertext[-16:] + ciphertext[:-16])
public_key = PublicKey(base64.b64decode(github_public_key))
sealed_key = SealedBox(public_key).encrypt(base64.b64encode(key))
Path(sealed_key_path).write_text(base64.b64encode(sealed_key).decode("ascii"), encoding="ascii")
Path(secret_key_path).write_text(base64.b64encode(key).decode("ascii"), encoding="ascii")
print("ENCRYPTED_SIZE=" + str(encrypted_output.stat().st_size))
print("ENCRYPTED_SHA256=" + hashlib.sha256(encrypted_output.read_bytes()).hexdigest())
print("PASS: encrypted full-repair baseline and sealed its key for GitHub Actions")
