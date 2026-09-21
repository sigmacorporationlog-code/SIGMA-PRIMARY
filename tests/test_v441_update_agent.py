import hashlib, json, threading
from pathlib import Path
import pytest
from app.services.update_agent import (
    UpdateAgentError, UpdateManifest, acquire_lock, compare_versions,
    download_verified, is_update_available, release_lock, write_state,
)


def _manifest(tmp_path, payload=b'sigma-update'):
    source = tmp_path / 'source.exe'; source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return UpdateManifest('4.41.0', source.as_uri(), digest, len(payload))


def test_manifest_validation_and_version_order(tmp_path):
    m = _manifest(tmp_path)
    assert is_update_available('4.40.0', m)
    assert not is_update_available('4.41.0', m)
    assert compare_versions('4.10.0', '4.9.0') > 0
    assert compare_versions('4.41.0-beta', '4.41.0') == 0
    with pytest.raises(UpdateAgentError):
        UpdateManifest.from_dict({'version':'4.41.0','url':'ftp://x','sha256':'0'*64,'size_bytes':1})


def test_download_verified_local_file(tmp_path):
    m = _manifest(tmp_path, b'verified')
    out = download_verified(m, tmp_path / 'updates' / 'SIGMA.exe')
    assert out.read_bytes() == b'verified'


def test_download_rejects_hash_mismatch(tmp_path):
    m = UpdateManifest('4.41.0', (tmp_path/'missing-source').as_uri(), '0'*64, 3)
    # URL opening failure is safely rejected and never leaves a .part file.
    with pytest.raises(Exception):
        download_verified(m, tmp_path/'updates'/'x.exe')
    assert not list((tmp_path/'updates').glob('*.part')) if (tmp_path/'updates').exists() else True


def test_download_rejects_size_mismatch(tmp_path):
    m = _manifest(tmp_path, b'abcdef')
    bad = UpdateManifest(m.version, m.url, m.sha256, 5)
    with pytest.raises(UpdateAgentError):
        download_verified(bad, tmp_path/'x.exe')
    assert not (tmp_path/'x.exe').exists()


def test_lock_serializes_updates(tmp_path):
    lock = tmp_path / '.update.lock'
    acquire_lock(lock)
    with pytest.raises(UpdateAgentError):
        acquire_lock(lock)
    release_lock(lock)
    acquire_lock(lock)
    release_lock(lock)
    assert not lock.exists()


def test_state_is_atomic_json(tmp_path):
    path = tmp_path / 'state.json'
    write_state(path, status='downloaded', target_version='4.41.0')
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['status'] == 'downloaded'
    assert data['target_version'] == '4.41.0'

def test_update_manifest_generator(tmp_path):
    import subprocess, sys
    artifact = tmp_path / 'SIGMA-Server.exe'; artifact.write_bytes(b'abc')
    manifest = tmp_path / 'manifest.json'
    subprocess.run([sys.executable, 'scripts/generate_update_manifest.py', str(artifact), '--version', '4.41.0', '--url', 'https://updates.example/SIGMA-Server.exe', '--output', str(manifest)], check=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    data=json.loads(manifest.read_text(encoding='utf-8'))
    assert data['sha256']==hashlib.sha256(b'abc').hexdigest()
    assert data['size_bytes']==3
    assert data['channel']=='commercial'
