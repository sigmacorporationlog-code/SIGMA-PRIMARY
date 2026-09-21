"""Secure, explicit deployment helper for a built SIGMA release.

Supports local Windows deployment and SSH/SCP deployment to a Linux host.
Remote deployment is opt-in and requires explicit environment variables.
"""
from __future__ import annotations
import argparse, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def local_windows(package: Path) -> None:
    if os.name != "nt": raise SystemExit("local-windows requires Windows")
    install_dir = Path(os.environ.get("SIGMA_INSTALL_DIR", r"C:\Program Files\SIGMA"))
    backup = Path(os.environ.get("SIGMA_BACKUP_DIR", r"C:\ProgramData\SIGMA\deploy-backups"))
    install_dir.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)
    # Never overwrite the current executable without first creating a backup.
    exe = install_dir / "SIGMA-Server.exe"
    if exe.exists():
        import shutil
        shutil.copy2(exe, backup / "SIGMA-Server.exe.previous")
    import shutil
    shutil.copy2(package, install_dir / package.name)
    print(f"PASS: artifact copied to {install_dir}")

def ssh_deploy(package: Path) -> None:
    host = os.environ.get("SIGMA_DEPLOY_HOST")
    user = os.environ.get("SIGMA_DEPLOY_USER")
    target = os.environ.get("SIGMA_DEPLOY_PATH")
    if not all((host, user, target)):
        raise SystemExit("SIGMA_DEPLOY_HOST, SIGMA_DEPLOY_USER and SIGMA_DEPLOY_PATH are required")
    if any(x in str(package) for x in ("..", "\n", "\r")): raise SystemExit("Unsafe package path")
    run(["scp", str(package), f"{user}@{host}:{target}/"])
    name = package.name
    command = f"cd '{target}' && sha256sum '{name}' && echo 'artifact staged; run server-specific activation separately'"
    run(["ssh", f"{user}@{host}", command])

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("artifact", type=Path)
    p.add_argument("--target", choices=("local-windows", "ssh"), required=True)
    args = p.parse_args()
    if not args.artifact.is_file(): raise SystemExit(f"Artifact not found: {args.artifact}")
    if args.target == "local-windows": local_windows(args.artifact)
    else: ssh_deploy(args.artifact)
    return 0

if __name__ == "__main__": raise SystemExit(main())
