"""Generate an Ed25519 key pair for SIGMA update manifest signing.

Run this in a secure/offline environment. Keep the private key outside the
application repository and CI logs. Only the public key is distributed to
update agents.
"""
from __future__ import annotations
import argparse, os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--private-out", type=Path, required=True)
    p.add_argument("--public-out", type=Path, required=True)
    args = p.parse_args()
    if args.private_out.exists() or args.public_out.exists():
        raise SystemExit("refusing to overwrite existing key material")
    key = Ed25519PrivateKey.generate()
    args.private_out.parent.mkdir(parents=True, exist_ok=True)
    args.public_out.parent.mkdir(parents=True, exist_ok=True)
    args.private_out.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    try:
        os.chmod(args.private_out, 0o600)
    except OSError:
        pass
    args.public_out.write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    print(f"private key: {args.private_out}")
    print(f"public key:  {args.public_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
