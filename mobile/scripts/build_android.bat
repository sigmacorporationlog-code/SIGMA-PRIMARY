@echo off
setlocal enabledelayedexpansion
REM Compile l'application Android SIGMA (wrapper WebView natif) sous Windows.
REM Equivalent de build_android.sh, pour PowerShell/cmd.exe sans Git Bash.
REM
REM Usage :
REM   scripts\build_android.bat debug
REM   scripts\build_android.bat release
REM   scripts\build_android.bat bundle
REM
REM Variables d'environnement reconnues : voir build_android.sh et
REM android\app\build.gradle (SIGMA_BASE_URL, SIGMA_APP_CHANNEL,
REM SIGMA_ANDROID_KEYSTORE, SIGMA_ANDROID_KEYSTORE_PASSWORD,
REM SIGMA_ANDROID_KEY_ALIAS, SIGMA_ANDROID_KEY_PASSWORD).

set "SCRIPT_DIR=%~dp0"
set "ANDROID_DIR=%SCRIPT_DIR%..\android"
set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=debug"

cd /d "%ANDROID_DIR%"

set "PROP_ARGS="
if not "%SIGMA_BASE_URL%"=="" set "PROP_ARGS=%PROP_ARGS% -PSIGMA_BASE_URL=%SIGMA_BASE_URL%"
if not "%SIGMA_APP_CHANNEL%"=="" set "PROP_ARGS=%PROP_ARGS% -PSIGMA_APP_CHANNEL=%SIGMA_APP_CHANNEL%"

if /i "%TARGET%"=="debug" (
    echo [SIGMA Android] Build DEBUG ^(non signe, pour test uniquement^)
    call gradlew.bat assembleDebug %PROP_ARGS%
    if errorlevel 1 exit /b 1
    echo APK : app\build\outputs\apk\debug\app-debug.apk
    goto :eof
)

if /i "%TARGET%"=="release" (
    if "%SIGMA_ANDROID_KEYSTORE%"=="" (
        echo [SIGMA Android] ATTENTION : SIGMA_ANDROID_KEYSTORE non defini - l'APK sortira NON SIGNE.
        echo Un APK non signe ne s'installe pas sur un telephone hors mode developpeur.
    )
    echo [SIGMA Android] Build RELEASE
    call gradlew.bat assembleRelease %PROP_ARGS%
    if errorlevel 1 exit /b 1
    echo APK : app\build\outputs\apk\release\app-release.apk
    goto :eof
)

if /i "%TARGET%"=="bundle" (
    if "%SIGMA_ANDROID_KEYSTORE%"=="" (
        echo [SIGMA Android] ERREUR : un .aab destine a Google Play doit etre signe.
        echo Definissez SIGMA_ANDROID_KEYSTORE / _PASSWORD / _KEY_ALIAS / _KEY_PASSWORD puis relancez.
        exit /b 1
    )
    echo [SIGMA Android] Build BUNDLE ^(.aab, Google Play^)
    call gradlew.bat bundleRelease %PROP_ARGS%
    if errorlevel 1 exit /b 1
    echo Bundle : app\build\outputs\bundle\release\app-release.aab
    goto :eof
)

echo Usage: %~nx0 {debug^|release^|bundle}
exit /b 1
