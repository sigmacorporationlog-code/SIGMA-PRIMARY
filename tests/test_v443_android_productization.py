from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_android_release_targets_and_version():
    release = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    gradle = (ROOT / 'mobile/android/app/build.gradle').read_text(encoding='utf-8')
    assert 'sigmaVersionCode' in gradle
    assert 'versionName sigmaReleaseVersion' in gradle
    assert release['release'].count('.') == 2
    assert "compileSdk 35" in gradle
    assert "targetSdk 35" in gradle


def test_installer_version_include_matches_release_manifest():
    release = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    inc = (ROOT / 'installer/version.iss.inc').read_text(encoding='utf-8')
    assert f'#define MyAppVersion "{release["release"]}"' in inc


def test_android_bundle_build_script_supports_apk_and_aab():
    script = (ROOT / 'scripts/build_android.sh').read_text(encoding='utf-8')
    assert 'debug|release|bundle' in script
    assert ':app:assembleDebug' in script
    assert ':app:assembleRelease' in script
    assert ':app:bundleRelease' in script
    assert "-PSIGMA_BASE_URL=\"$BASE_URL\"" in script


def test_android_security_and_deep_link_contract():
    manifest = (ROOT / 'mobile/android/app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')
    activity = (ROOT / 'mobile/android/app/src/main/java/com/sigma/school/MainActivity.java').read_text(encoding='utf-8')
    assert 'android:usesCleartextTraffic="false"' in manifest
    assert 'android.permission.POST_NOTIFICATIONS' in manifest
    assert 'android:scheme="sigma" android:host="open"' in manifest
    assert 'MIXED_CONTENT_NEVER_ALLOW' in activity
    assert 'setAllowFileAccess(false)' in activity
    assert 'setAllowContentAccess(false)' in activity
    assert 'isAllowed(candidate)' in activity


def test_ci_publishes_debug_apk_and_release_aab():
    ci = (ROOT / '.github/workflows/ci-android.yml').read_text(encoding='utf-8')
    assert ':app:assembleDebug :app:bundleRelease' in ci
    assert 'SIGMA-Android-debug.apk' in ci
    assert 'SIGMA-Android-release.aab' in ci
    assert 'sigma-android-artifacts' in ci
