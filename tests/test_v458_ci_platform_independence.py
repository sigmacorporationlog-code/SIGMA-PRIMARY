"""Vérifie que les pipelines CI Windows et Android sont réellement
indépendants (demande explicite du 20/09/2026) : avant cette date, un seul
fichier ci.yml faisait dépendre l'un de l'autre — un job final `release`
exigeait que windows-installer ET android-build réussissent tous les deux,
et le job android-build dépendait lui-même du job `test` (suite Python),
alors que la compilation d'un wrapper WebView Android n'a besoin d'aucun
code Python pour réussir. Un échec Android bloquait donc la publication
Windows, et réciproquement.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _jobs(workflow_filename: str) -> dict:
    text = (ROOT / ".github/workflows" / workflow_filename).read_text(encoding="utf-8")
    return yaml.safe_load(text)["jobs"]


def _needs(job: dict) -> set[str]:
    needs = job.get("needs") or []
    return {needs} if isinstance(needs, str) else set(needs)


def test_windows_and_android_workflows_are_separate_files():
    assert (ROOT / ".github/workflows/ci-windows.yml").is_file()
    assert (ROOT / ".github/workflows/ci-android.yml").is_file()
    # L'ancien fichier fusionné ne doit plus exister, pour ne pas déclencher
    # une troisième exécution redondante en plus des deux nouveaux.
    assert not (ROOT / ".github/workflows/ci.yml").exists()


def test_windows_jobs_never_depend_on_android_jobs():
    windows_jobs = _jobs("ci-windows.yml")
    android_job_names = set(_jobs("ci-android.yml").keys())
    for name, job in windows_jobs.items():
        overlap = _needs(job) & android_job_names
        assert not overlap, f"le job Windows '{name}' dépend d'un job Android: {overlap}"


def test_android_jobs_never_depend_on_windows_jobs_or_python_tests():
    android_jobs = _jobs("ci-android.yml")
    windows_job_names = set(_jobs("ci-windows.yml").keys())  # inclut le job 'test' Python
    for name, job in android_jobs.items():
        overlap = _needs(job) & windows_job_names
        assert not overlap, f"le job Android '{name}' dépend d'un job Windows/Python: {overlap}"


def test_each_platform_publishes_its_own_release_independently():
    windows_jobs = _jobs("ci-windows.yml")
    android_jobs = _jobs("ci-android.yml")
    assert "release-windows" in windows_jobs
    assert "release-android" in android_jobs
    # Chaque job de release cible explicitement le même tag (github.ref_name)
    # plutôt que de compter sur l'ordre d'exécution entre les deux workflows
    # indépendants, qui n'est pas garanti.
    for job in (windows_jobs["release-windows"], android_jobs["release-android"]):
        run_step = next(s for s in job["steps"] if "softprops/action-gh-release" in str(s.get("uses", "")))
        assert run_step["with"]["tag_name"] == "${{ github.ref_name }}"


def test_windows_installer_artifact_path_is_version_independent():
    # Un chemin comme release_out/4.46.0/SIGMA-4.46.0-Setup.exe, codé en dur
    # dans les champs path:/files: du workflow (pas dans un commentaire),
    # casse silencieusement dès la prochaine version.
    windows_jobs = _jobs("ci-windows.yml")
    for job in windows_jobs.values():
        for step in job.get("steps", []):
            with_block = step.get("with") or {}
            for field in ("path", "files"):
                value = with_block.get(field)
                if value:
                    assert "4.46.0" not in str(value), f"chemin figé sur la version: {value!r}"
    ci = (ROOT / ".github/workflows/ci-windows.yml").read_text(encoding="utf-8")
    assert "release_out/SIGMA-Setup.exe" in ci
