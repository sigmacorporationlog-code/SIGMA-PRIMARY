from pathlib import Path


def test_administration_ui_exposes_correction_actions():
    html=(Path(__file__).parents[1]/"static/administration.html").read_text(encoding="utf-8")
    for token in ["editLevel", "deactivateLevel", "restoreLevel", "editStream", "deactivateStream", "restoreStream", "editClass", "deactivateClass", "restoreClass"]:
        assert token in html


def test_installer_is_headless_and_opens_dashboard():
    iss=(Path(__file__).parents[1]/"installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert "SIGMAPrimaireServer" in iss
    assert "--service" in iss
    assert "runhidden" in iss
    assert "open_sigma.vbs" in iss
    assert (Path(__file__).parents[1]/"OUVRIR_SIGMA.vbs").exists()
