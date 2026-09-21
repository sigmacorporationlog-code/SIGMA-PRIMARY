"""Generate a SIGMA update manifest, optionally authenticated with Ed25519.

The private key is read only for signing and is never copied into the output.
Production release pipelines should always pass --private-key and --key-id.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.services.update_agent import canonical_manifest_bytes


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sign(data: dict, private_key_path: Path) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("private key must be Ed25519")
    return base64.b64encode(key.sign(canonical_manifest_bytes(data))).decode("ascii")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("artifact", type=Path)
    p.add_argument("--version", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--channel", default="commercial")
    p.add_argument("--min-version")
    p.add_argument("--notes", default="")
    p.add_argument("--private-key", type=Path)
    p.add_argument("--key-id")
    p.add_argument("--require-signature", action="store_true")
    p.add_argument("--output", type=Path, default=Path("update-manifest.json"))
    args = p.parse_args()
    if not args.artifact.is_file():
        raise SystemExit("artifact not found")
    if bool(args.private_key) != bool(args.key_id):
        raise SystemExit("--private-key and --key-id must be supplied together")
    if args.require_signature and not args.private_key:
        raise SystemExit("signature required: supply --private-key and --key-id")
    data = {
        "product": "SIGMA",
        "manifest_version": 2,
        "version": args.version,
        "url": args.url,
        "sha256": digest(args.artifact),
        "size_bytes": args.artifact.stat().st_size,
        "channel": args.channel,
    }
    if args.min_version:
        data["min_version"] = args.min_version
    if args.notes:
        data["notes"] = args.notes
    if args.private_key:
        data["key_id"] = args.key_id
        data["signature_algorithm"] = "ed25519"
        data["signature"] = sign(data, args.private_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not args.private_key:
        print("WARNING: integrity-only manifest; production update agents should require Ed25519 signatures", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
