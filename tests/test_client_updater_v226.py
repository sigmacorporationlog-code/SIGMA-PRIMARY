from pathlib import Path
import hashlib, json, zipfile

from app.services.client_updater import UpdateError, load_manifest, update_client


def make_package(tmp_path: Path, version="2.26.0"):
    root = tmp_path / "pkgroot"
    root.mkdir()
    (root / "SIGMA-Client.txt").write_text(version, encoding="utf-8")
    package = tmp_path / "client.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(root / "SIGMA-Client.txt", "sigma-client/SIGMA-Client.txt")
    return package


def manifest_for(tmp_path, package, version="2.26.0"):
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"version": version, "package_sha256": sha,
                             "package_size": package.stat().st_size,
                             "package_url": package.resolve().as_uri()}), encoding="utf-8")
    return m


def test_manifest_rejects_non_https(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"version":"2.26.0","package_sha256":"0"*64,"package_size":1,"package_url":"http://x"}), encoding="utf-8")
    try:
        load_manifest(m)
        assert False
    except UpdateError:
        pass


def test_update_verifies_hash_and_installs(tmp_path):
    package = make_package(tmp_path)
    manifest = manifest_for(tmp_path, package)
    install = tmp_path / "client"
    install.mkdir(); (install / "old.txt").write_text("old")
    result = update_client(current_version="2.25.0", manifest_path=manifest, install_dir=install, backup_root=tmp_path / "backups")
    assert result["status"] == "updated"
    assert (install / "SIGMA-Client.txt").read_text(encoding="utf-8") == "2.26.0"
    assert not (install / "old.txt").exists()
    assert Path(result["backup_dir"]).exists()


def test_update_rejects_tampered_package(tmp_path):
    package = make_package(tmp_path)
    manifest = manifest_for(tmp_path, package)
    package.write_bytes(package.read_bytes() + b"tamper")
    install = tmp_path / "client"; install.mkdir(); (install / "old.txt").write_text("old")
    try:
        update_client(current_version="2.25.0", manifest_path=manifest, install_dir=install, backup_root=tmp_path / "backups")
        assert False
    except UpdateError as exc:
        assert "manifest" in str(exc) or "SHA-256" in str(exc)
    assert (install / "old.txt").read_text(encoding="utf-8") == "old"
