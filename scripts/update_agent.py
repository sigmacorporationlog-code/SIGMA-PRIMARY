"""SIGMA V4.43 trusted update agent CLI.

Production mode requires an Ed25519-signed manifest and a trusted public key.
Unsigned manifests are accepted only with the explicit --allow-unsigned switch,
which is intended for local development/legacy migration and is never implicit.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.services.update_agent import (
    UpdateAgentError, acquire_lock, download_verified, is_update_available,
    load_manifest, load_trusted_manifest, release_lock, write_state,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--current-version", required=True)
    p.add_argument("--public-key", type=Path, default=Path(os.environ["SIGMA_UPDATE_PUBLIC_KEY"]) if os.environ.get("SIGMA_UPDATE_PUBLIC_KEY") else None)
    p.add_argument("--expected-key-id", default=os.environ.get("SIGMA_UPDATE_KEY_ID"))
    p.add_argument("--allow-unsigned", action="store_true")
    p.add_argument("--download-dir", type=Path, default=Path(os.environ.get("SIGMA_UPDATE_DIR", "updates")))
    p.add_argument("--state", type=Path, default=Path(os.environ.get("SIGMA_UPDATE_STATE", "update-state.json")))
    p.add_argument("--check", action="store_true")
    p.add_argument("--activate", action="store_true")
    p.add_argument("--install-dir", type=Path, default=Path(os.environ.get("SIGMA_INSTALL_DIR", r"C:\Program Files\SIGMA")))
    args = p.parse_args()
    try:
        if args.allow_unsigned:
            manifest = load_manifest(args.manifest)
            trust = "UNSIGNED_EXPLICITLY_ALLOWED"
        else:
            if not args.public_key:
                raise UpdateAgentError("clé publique de mise à jour requise (SIGMA_UPDATE_PUBLIC_KEY ou --public-key)")
            manifest = load_trusted_manifest(args.manifest, args.public_key, expected_key_id=args.expected_key_id)
            trust = f"ED25519:{manifest.key_id}"
        available = is_update_available(args.current_version, manifest)
        result = {
            "available": available,
            "current_version": args.current_version,
            "target_version": manifest.version,
            "channel": manifest.channel,
            "manifest_trust": trust,
        }
        if not available or args.check:
            write_state(args.state, status="checked", **result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        lock = args.download_dir / ".update.lock"
        acquire_lock(lock)
        try:
            artifact = args.download_dir / f"SIGMA-{manifest.version}.exe"
            download_verified(manifest, artifact)
            result["artifact"] = str(artifact)
            result["sha256"] = manifest.sha256
            result["status"] = "downloaded"
            if args.activate:
                if os.name != "nt":
                    raise UpdateAgentError("activation nécessite Windows")
                from app.services.deployment_guard import activate_windows_executable
                deployed = activate_windows_executable(artifact, args.install_dir)
                result.update({"status": deployed.status, "deployment_message": deployed.message})
            write_state(args.state, **result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        finally:
            release_lock(lock)
    except UpdateAgentError as exc:
        write_state(args.state, status="blocked", error=str(exc))
        print(f"UPDATE BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        write_state(args.state, status="failed", error=str(exc))
        print(f"UPDATE FAILED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
