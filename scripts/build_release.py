"""Reproducible SIGMA release orchestrator.

Builds a clean source bundle and, on Windows, optionally invokes PyInstaller
and Inno Setup. The script never publishes an artifact unless every requested
stage succeeds.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDES = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "sigma.db", "restore_staging", "build", "dist", "release_out"}

def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def copy_clean(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        if item.name in EXCLUDES or item.name.startswith("release_"):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(*EXCLUDES, "*.pyc"))
        else:
            shutil.copy2(item, target)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--version", default=None)
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--windows", action="store_true")
    p.add_argument("--installer", action="store_true")
    args = p.parse_args()
    manifest = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    version = args.version or manifest["release"]
    if version != manifest["release"]:
        raise SystemExit(f"Version mismatch: --version={version}, release.json={manifest['release']}")
    if not args.skip_tests:
        run([sys.executable, "-m", "compileall", "-q", "app", "alembic", "run_server.py", "seed.py"])
        run([sys.executable, "-m", "pytest", "-q"])
    if args.windows:
        if os.name != "nt":
            raise SystemExit("--windows requires Windows")
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "build_windows.ps1", "-Clean"])
        exe = ROOT / "dist" / "SIGMA-Server.exe"
        if not exe.exists():
            raise SystemExit("Windows build did not produce dist/SIGMA-Server.exe")
        if args.installer:
            iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
            if not iscc:
                raise SystemExit("Inno Setup Compiler (ISCC.exe) is required for --installer")
            run([iscc, str(ROOT / "installer" / "SIGMA-Setup.iss")])
    out = ROOT / "release_out" / version
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="sigma_release_") as tmp:
        staging = Path(tmp) / "SIGMA"
        staging.mkdir()
        copy_clean(ROOT, staging)
        archive = out / f"SIGMA_{version}_SOURCE.zip"
        shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=staging.parent, base_dir=staging.name)
    records = []
    for f in sorted(out.rglob("*")):
        if f.is_file(): records.append({"file": f.relative_to(out).as_posix(), "sha256": sha256(f), "bytes": f.stat().st_size})
    (out / "SHA256SUMS.json").write_text(json.dumps({"release": version, "artifacts": records}, indent=2), encoding="utf-8")
    print(f"PASS: release artifacts in {out}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
