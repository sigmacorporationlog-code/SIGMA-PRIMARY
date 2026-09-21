from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_android_offline_queue_has_non_destructive_ack_contract():
    queue = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/SecureOfflineQueue.java').read_text(encoding='utf-8')
    bridge = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/SigmaMobileBridge.java').read_text(encoding='utf-8')
    assert 'peekJson()' in queue
    assert 'ackJson(String operationIdsJson)' in queue
    assert 'peekSyncOperations' in bridge
    assert 'ackSyncOperations' in bridge
    assert 'Legacy destructive API' in queue
