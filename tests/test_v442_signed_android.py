import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.update_agent import (
    UpdateAgentError,
    canonical_manifest_bytes,
    load_trusted_manifest,
    verify_manifest_signature,
)

ROOT = Path(__file__).resolve().parents[1]


def _keys(tmp_path):
    private = Ed25519PrivateKey.generate()
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    private_path.write_bytes(private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_path.write_bytes(private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    return private, private_path, public_path


def test_signed_manifest_verifies_and_tampering_is_rejected(tmp_path):
    private, _, public_path = _keys(tmp_path)
    data = {
        "product": "SIGMA",
        "manifest_version": 2,
        "version": "4.45.0",
        "url": "https://updates.example/SIGMA-Server.exe",
        "sha256": "a" * 64,
        "size_bytes": 123,
        "channel": "commercial",
        "key_id": "test-key",
        "signature_algorithm": "ed25519",
    }
    data["signature"] = base64.b64encode(private.sign(canonical_manifest_bytes(data))).decode("ascii")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    manifest = load_trusted_manifest(path, public_path, expected_key_id="test-key")
    assert manifest.version == "4.45.0"
    assert manifest.key_id == "test-key"
    data["version"] = "9.9.9"
    with pytest.raises(UpdateAgentError):
        verify_manifest_signature(data, public_path)


def test_manifest_generator_can_sign(tmp_path):
    _, private_path, public_path = _keys(tmp_path)
    artifact = tmp_path / "SIGMA-Server.exe"
    artifact.write_bytes(b"signed-artifact")
    out = tmp_path / "manifest.json"
    subprocess.run([
        sys.executable,
        "scripts/generate_update_manifest.py",
        str(artifact),
        "--version", "4.45.0",
        "--url", "https://updates.example/SIGMA-Server.exe",
        "--private-key", str(private_path),
        "--key-id", "prod-key-1",
        "--require-signature",
        "--output", str(out),
    ], cwd=ROOT, check=True)
    m = load_trusted_manifest(out, public_path, expected_key_id="prod-key-1")
    assert m.signature_algorithm == "ed25519"


def test_android_project_security_and_build_pipeline():
    manifest = (ROOT / "mobile/android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    java = (ROOT / "mobile/android/app/src/main/java/com/sigma/school/MainActivity.java").read_text(encoding="utf-8")
    gradle = (ROOT / "mobile/android/app/build.gradle").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci-android.yml").read_text(encoding="utf-8")
    assert 'android:usesCleartextTraffic="false"' in manifest
    assert "MIXED_CONTENT_NEVER_ALLOW" in java
    assert "setAllowFileAccess(false)" in java
    assert "setAcceptThirdPartyCookies(view, false)" in java
    assert "SIGMA_BASE_URL" in gradle
    assert "compileSdk 35" in gradle
    assert "android-build:" in ci
    assert "assembleDebug" in ci
    assert "SIGMA-Android-debug.apk" in ci


def test_android_release_metadata_is_current():
    gradle = (ROOT / "mobile/android/app/build.gradle").read_text(encoding="utf-8")
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    assert release["release"] == "4.46.0"
    assert "versionName sigmaReleaseVersion" in gradle
    assert "versionCode sigmaVersionCode" in gradle
    assert release["integrity"] == "sha256+ed25519"
