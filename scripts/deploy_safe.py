"""Explicit production deployment wrapper.

Requires a staged artifact and delegates activation to the deployment guard.
It is intentionally Windows-only for service activation and never disables the
health gate or rollback path.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from app.services.deployment_guard import activate_windows_executable, write_deployment_state


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("artifact", type=Path)
    p.add_argument("--install-dir", default=os.environ.get("SIGMA_INSTALL_DIR", r"C:\Program Files\SIGMA"))
    p.add_argument("--state", default=os.environ.get("SIGMA_DEPLOYMENT_STATE", r"C:\ProgramData\SIGMA\deployment-state.json"))
    args = p.parse_args()
    result = activate_windows_executable(args.artifact, Path(args.install_dir))
    write_deployment_state(Path(args.state), result)
    print(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
