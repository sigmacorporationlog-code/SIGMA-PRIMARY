from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_release_is_v444_mobile():
    data = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    assert data['release'] == '4.46.0'
    assert data['minimum_previous_release'] == '4.45.0'
    assert 'hardening' in data['title'].lower()


def test_android_secure_offline_queue_and_bridge():
    queue = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/SecureOfflineQueue.java').read_text(encoding='utf-8')
    bridge = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/SigmaMobileBridge.java').read_text(encoding='utf-8')
    assert 'AndroidKeyStore' in queue
    assert 'AES/GCM/NoPadding' in queue
    assert 'enqueueSyncOperation' in bridge
    assert 'drainSyncOperations' in bridge


def test_android_native_notifications_and_network_awareness():
    activity = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/MainActivity.java').read_text(encoding='utf-8')
    manifest = (ROOT / 'mobile/android/app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')
    assert 'NotificationChannel' in activity
    assert 'NotificationCompat.Builder' in activity
    assert '/api/notifications?unread_only=true' in activity
    assert 'hasNetwork()' in activity
    assert 'POST_NOTIFICATIONS' in manifest


def test_android_build_and_ci_release_artifact_contract():
    gradle = (ROOT / 'mobile/android/app/build.gradle').read_text(encoding='utf-8')
    ci = (ROOT / '.github/workflows/ci-android.yml').read_text(encoding='utf-8')
    assert "versionCode sigmaVersionCode" in gradle
    assert "versionName sigmaReleaseVersion" in gradle
    assert "androidx.core:core:1.15.0" in gradle
    assert 'sigma-android-artifacts' in ci
    assert 'SIGMA-Android-release.aab' in ci
    assert 'SIGMA-Android-debug.apk' in ci
