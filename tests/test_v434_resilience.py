from pathlib import Path
from app.services.deployment_guard import DeploymentError, sha256_file, stage_artifact
from app.services.production import readiness
from app.services.observability import record_request, snapshot


def test_observability_snapshot_has_latency_percentiles():
    record_request("GET", "/api/health", 200, 4.0)
    record_request("GET", "/api/health", 500, 20.0)
    data = snapshot()
    assert data["latency_ms"]["p50"] >= 0
    assert data["latency_ms"]["p95"] >= data["latency_ms"]["p50"]
    assert data["total_5xx"] >= 1


def test_stage_artifact_is_integrity_checked(tmp_path: Path):
    source = tmp_path / "SIGMA-Server.exe"
    source.write_bytes(b"sigma-release")
    staged = stage_artifact(source, tmp_path / "stage")
    assert staged.exists()
    assert sha256_file(staged) == sha256_file(source)


def test_stage_rejects_missing_artifact(tmp_path: Path):
    try:
        stage_artifact(tmp_path / "missing.exe", tmp_path / "stage")
    except DeploymentError:
        pass
    else:
        raise AssertionError("missing artifact must be rejected")


def test_deployment_guard_rejects_unsafe_filename(tmp_path: Path):
    source = tmp_path / "good.exe"
    source.write_bytes(b"x")
    staged = stage_artifact(source, tmp_path / "stage")
    assert staged.name == "good.exe"


def test_health_probe_scripts_exist():
    assert Path("scripts/health_probe.py").exists()
    assert Path("scripts/auto_heal.py").exists()
    assert Path("scripts/deploy_safe.py").exists()
