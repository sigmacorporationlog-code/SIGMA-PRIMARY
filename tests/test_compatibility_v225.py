from pathlib import Path
from app.services.compatibility import compatibility, parse_version


def test_version_parsing():
    assert parse_version('2.25.0-primary-commercial').minor == 25


def test_supported_older_client():
    assert compatibility('2.24.0-primary-commercial', '2.25.0-primary-commercial')['compatible'] is True


def test_minimum_supported_client():
    assert compatibility('2.19.0-primary-commercial', '2.25.0-primary-commercial')['reason'] == 'client_too_old'


def test_future_client_blocked():
    assert compatibility('2.26.0-primary-commercial', '2.25.0-primary-commercial')['reason'] == 'client_newer_than_server'


def test_major_mismatch_blocked():
    assert compatibility('3.0.0', '2.25.0-primary-commercial')['reason'] == 'major_version_mismatch'


def test_api_and_client_hooks_present():
    root=Path(__file__).parents[1]
    assert '/compatibility' in (root/'app/api/sync.py').read_text(encoding='utf-8')
    assert 'def check_compatibility' in (root/'app/services/sync_client.py').read_text(encoding='utf-8')
    assert 'APP_VERSION' in (root/'app/core/config.py').read_text(encoding='utf-8')


def test_device_listing_exposes_compatibility():
    root=Path(__file__).parents[1]
    src=(root/'app/api/sync.py').read_text(encoding='utf-8')
    assert '"compatibility": compatibility' in src
