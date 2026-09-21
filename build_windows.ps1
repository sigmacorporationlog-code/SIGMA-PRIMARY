# SIGMA Windows commercial build - zero-manipulation launcher
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$LogDir = Join-Path $Root "release_out\build_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("build-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
try { Start-Transcript -Path $Log -Force | Out-Null } catch {
    New-Item -ItemType File -Force -Path $Log | Out-Null
}

function Fail([string]$Message) { throw "[SIGMA BUILD] $Message" }
function Run([string]$File, [string[]]$CommandArgs) {
    Write-Host ">> $File $($CommandArgs -join ' ')" -ForegroundColor Cyan
    & $File @CommandArgs
    if ($LASTEXITCODE -ne 0) { Fail "Commande échouée ($LASTEXITCODE): $File" }
}
function Get-Python313Path {
    $candidates = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $resolved = (& py -3.13 -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1).Trim()
            if ($LASTEXITCODE -eq 0 -and $resolved -and (Test-Path $resolved)) { $candidates += $resolved }
        } catch { }
    }
    $candidates += @(
        (Join-Path $env:LocalAppData "Programs\Python\Python313\python.exe"),
        (Join-Path $env:ProgramFiles "Python313\python.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Python313\python.exe")
    )
    return ($candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1)
}
function Test-Python313 {
    $python = Get-Python313Path
    if (-not $python) { return $false }
    & $python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,13) else 1)" 2>$null
    return ($LASTEXITCODE -eq 0)
}
function Ensure-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "winget est absent. Sur une machine de compilation Windows, installez Python 3.13 et Inno Setup une seule fois, puis relancez."
    }
}
function Ensure-Python313 {
    if (Test-Python313) { return }
    Ensure-Winget
    Write-Host "Python 3.13 absent : installation automatique..." -ForegroundColor Yellow
    Run "winget" @("install","--id","Python.Python.3.13","--exact","--accept-package-agreements","--accept-source-agreements","--silent")
    Refresh-PathFromRegistry
    Start-Sleep -Seconds 2
    if (-not (Test-Python313)) { Fail "Python 3.13 n'a pas pu être détecté après installation automatique." }
}
function Refresh-PathFromRegistry {
    # winget met à jour le PATH dans le registre (Machine et/ou User), mais le
    # processus PowerShell courant garde en mémoire le PATH chargé au
    # démarrage. Sans ce rafraîchissement, Get-Command ne voit jamais un
    # exécutable tout juste installé, même une fois l'installation terminée.
    try {
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = @($machinePath, $userPath) -join ";"
    } catch { }
}
function Get-InnoSetupCandidatePaths {
    @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LocalAppData "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LocalAppData "Inno Setup 6\ISCC.exe")
    )
}
function Find-InnoSetup {
    if ($env:SIGMA_ISCC_PATH -and (Test-Path $env:SIGMA_ISCC_PATH)) { return $env:SIGMA_ISCC_PATH }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return (Get-InnoSetupCandidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1)
}
function Ensure-InnoSetup {
    $found = Find-InnoSetup
    if ($found) { return $found }
    Ensure-Winget
    Write-Host "Inno Setup absent : installation automatique..." -ForegroundColor Yellow
    Run "winget" @("install","--id","JRSoftware.InnoSetup","--exact","--accept-package-agreements","--accept-source-agreements","--silent")
    # L'installateur peut finir d'écrire sur disque/registre juste après le
    # retour de winget ; on relit le PATH et on retente sur quelques secondes
    # avant d'abandonner, plutôt que d'échouer sur une seule vérification
    # immédiate.
    for ($i = 0; $i -lt 5; $i++) {
        Refresh-PathFromRegistry
        $found = Find-InnoSetup
        if ($found) { return $found }
        Start-Sleep -Seconds 2
    }
    Fail ("Inno Setup n'a pas pu être détecté après installation automatique. " +
        "Installez-le manuellement depuis https://jrsoftware.org/isdl.php, ou si vous " +
        "connaissez son emplacement, définissez la variable d'environnement " +
        "SIGMA_ISCC_PATH avec le chemin complet de ISCC.exe puis relancez le build.")
}
function Get-Version {
    $release = Get-Content (Join-Path $Root "release.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$release.release)) { Fail "release.json ne contient pas de version." }
    return [string]$release.release
}
function Show-Result([bool]$Ok, [string]$Message) {
    try {
        Add-Type -AssemblyName PresentationFramework -ErrorAction Stop
        $icon = if ($Ok) { 'Information' } else { 'Error' }
        [System.Windows.MessageBox]::Show($Message, "SIGMA — Build Windows", 'OK', $icon) | Out-Null
    } catch { Write-Host $Message }
}

$Ok = $false
$Message = ""
try {
    if ($env:OS -ne "Windows_NT") { Fail "Ce build doit être exécuté sous Windows." }
    $Version = Get-Version
    $InnoVersionInclude = Join-Path $Root "installer\version.iss.inc"
    Set-Content -Encoding ASCII -Path $InnoVersionInclude -Value ('#define MyAppVersion "' + $Version + '"')
    $BuildRoot = Join-Path $Root "build\commercial_$Version"
    $Venv = Join-Path $BuildRoot ".venv"
    $Dist = Join-Path $BuildRoot "dist"
    $Work = Join-Path $BuildRoot "pyi_work"
    $ReleaseDir = Join-Path $Root "release_out\$Version"

    if ($Clean) {
        foreach ($p in @((Join-Path $Root "build"),(Join-Path $Root "dist"),(Join-Path $Root "release_out\$Version"))) {
            if (Test-Path $p) { Remove-Item -Recurse -Force $p }
        }
    }
    New-Item -ItemType Directory -Force -Path $BuildRoot,$ReleaseDir | Out-Null

    Ensure-Python313
    $SystemPython = Get-Python313Path
    if (-not $SystemPython) { Fail "Python 3.13 est installé mais son exécutable est introuvable." }
    if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
        Run $SystemPython @("-m","venv",$Venv)
    }
    $Vpy = Join-Path $Venv "Scripts\python.exe"
    if (-not (Test-Path $Vpy)) { Fail "Environnement Python de build introuvable." }
    $bits = (& $Vpy -c "import struct; print(8*struct.calcsize('P'))" | Select-Object -Last 1).Trim()
    if ($LASTEXITCODE -ne 0 -or $bits -ne "64") { Fail "Python 3.13 64 bits est requis." }

    Write-Host "[1/8] Dépendances..." -ForegroundColor Green
    Run $Vpy @("-m","pip","install","--upgrade","pip","wheel")
    Run $Vpy @("-m","pip","install","-r",(Join-Path $Root "requirements.txt"))
    Run $Vpy @("-m","pip","install","-r",(Join-Path $Root "requirements-build.txt"))
    Run $Vpy @("-m","pip","install","pyinstaller>=6.22,<7")
    Run $Vpy @("-m","pip","check")

    Write-Host "[2/8] Contrôles source/release..." -ForegroundColor Green
    Run $Vpy @("tools_release_gate.py")
    Run $Vpy @("-m","compileall","-q","app","alembic","run_server.py","seed.py")
    # compileall ne valide que la syntaxe. Cet import réel est le seul contrôle
    # qui détecte une dépendance absente de requirements.txt avant que
    # PyInstaller ne fige un exécutable incapable de démarrer.
    Run $Vpy @("-c","import app.main; print('Import applicatif OK:', len(app.main.app.routes), 'routes')")

    if (-not $SkipTests) {
        Write-Host "[3/8] Tests de non-régression..." -ForegroundColor Green
        Run $Vpy @("-m","pytest","-q","--junitxml",(Join-Path $LogDir "pytest-$Version.xml"))
    } else { Write-Host "[3/8] Tests ignorés explicitement." -ForegroundColor Yellow }

    Write-Host "[4/8] PyInstaller..." -ForegroundColor Green
    if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
    if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }
    Run $Vpy @("-m","PyInstaller","--clean","--noconfirm","--distpath",$Dist,"--workpath",$Work,(Join-Path $Root "sigma.spec"))
    # Build « onedir » : dist\SIGMA-Server\SIGMA-Server.exe + dist\SIGMA-Server\_internal\
    $AppDir = Join-Path $Dist "SIGMA-Server"
    $Exe = Join-Path $AppDir "SIGMA-Server.exe"
    if (-not (Test-Path $Exe)) { Fail "SIGMA-Server.exe absent après PyInstaller." }
    $Internal = Join-Path $AppDir "_internal"
    if (-not (Test-Path $Internal)) { Fail "Dossier _internal absent : le paquet autonome serait incomplet." }
    foreach ($needed in @("static","alembic","alembic.ini")) {
        if (-not (Test-Path (Join-Path $Internal $needed))) { Fail "Ressource embarquée absente : $needed" }
    }
    $AppSize = (Get-ChildItem -Recurse -File $AppDir | Measure-Object -Property Length -Sum).Sum
    if ($AppSize -lt 20MB) { Fail "Le paquet SIGMA-Server est anormalement petit." }
    Write-Host "SIGMA-Server.exe généré avec succès." -ForegroundColor Green

    Write-Host "[5/8] Smoke test autonome..." -ForegroundColor Green
    $Smoke = Join-Path $env:TEMP ("sigma-smoke-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
    $old = @($env:SIGMA_DATA_DIR,$env:OPEN_BROWSER,$env:PORT,$env:BIND_HOST)
    $proc = $null
    try {
        $env:SIGMA_DATA_DIR=$Smoke; $env:OPEN_BROWSER="false"; $env:PORT="18765"; $env:BIND_HOST="127.0.0.1"
        # L'exécutable est compilé en sous-système fenêtré (console=False) :
        # l'opérateur « & » de PowerShell ne l'attendrait pas et $LASTEXITCODE
        # serait celui de la commande précédente. Start-Process -Wait est donc
        # obligatoire ici, sinon le smoke test validerait un build cassé.
        $setup = Start-Process -FilePath $Exe -ArgumentList "--setup" -PassThru -Wait -WindowStyle Hidden
        if ($setup.ExitCode -ne 0) { Fail "SIGMA-Server.exe --setup a échoué (code $($setup.ExitCode))." }
        if (-not (Test-Path (Join-Path $Smoke ".env"))) { Fail "--setup n'a pas produit de fichier .env." }
        $proc = Start-Process -FilePath $Exe -PassThru -WindowStyle Hidden
        $healthy = $false
        for ($i=0; $i -lt 60; $i++) {
            Start-Sleep -Milliseconds 500
            if ($proc.HasExited) { Fail "Le serveur autonome s'est arrêté (code $($proc.ExitCode))." }
            try {
                $r=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:18765/api/health/live" -TimeoutSec 2
                if ($r.StatusCode -eq 200) { $healthy=$true; break }
            } catch { }
        }
        if (-not $healthy) { Fail "Le serveur autonome ne répond pas à /api/health/live." }
        $dash=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:18765/dashboard/" -TimeoutSec 5
        if ($dash.StatusCode -ne 200) { Fail "Dashboard embarqué inaccessible." }
    } finally {
        if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        $env:SIGMA_DATA_DIR=$old[0]; $env:OPEN_BROWSER=$old[1]; $env:PORT=$old[2]; $env:BIND_HOST=$old[3]
        Remove-Item -Recurse -Force $Smoke -ErrorAction SilentlyContinue
    }

    Write-Host "[6/8] Publication portable..." -ForegroundColor Green
    $Portable = Join-Path $Root "release_out\portable"
    if (Test-Path $Portable) { Remove-Item -Recurse -Force $Portable }
    New-Item -ItemType Directory -Force -Path $Portable | Out-Null
    # Inno Setup référence un chemin dist stable à la racine : on y publie le
    # dossier applicatif validé par le smoke test.
    $RootDist = Join-Path $Root "dist\SIGMA-Server"
    if (Test-Path $RootDist) { Remove-Item -Recurse -Force $RootDist }
    New-Item -ItemType Directory -Force -Path $RootDist | Out-Null
    Copy-Item (Join-Path $AppDir "*") $RootDist -Recurse -Force

    $PortableApp = Join-Path $Portable "SIGMA-$Version-Windows-x64"
    New-Item -ItemType Directory -Force -Path $PortableApp | Out-Null
    Copy-Item (Join-Path $AppDir "*") $PortableApp -Recurse -Force
    Copy-Item (Join-Path $Root "open_sigma.vbs") $PortableApp -Force
    Copy-Item (Join-Path $Root "ARRETER_SIGMA.vbs") $PortableApp -Force
    $FinalExe = Join-Path $PortableApp "SIGMA-Server.exe"
    $Hash = (Get-FileHash -Algorithm SHA256 $FinalExe).Hash.ToLowerInvariant()
    Set-Content -Encoding ASCII -Path (Join-Path $Portable "SIGMA-Server-$Version-Windows-x64.sha256") -Value "$Hash  SIGMA-Server.exe"
    @("SIGMA $Version — paquet Windows autonome","","Décompressez le dossier puis double-cliquez sur SIGMA-Server.exe.","Pour arrêter le serveur : double-cliquez sur ARRETER_SIGMA.vbs.","Python et les dépendances ne sont pas nécessaires sur le PC cible.","Gardez le dossier _internal à côté de l'exécutable : il contient l'interpréteur et les ressources.","Données persistantes : %PROGRAMDATA%\SIGMA (ou le dossier indiqué par SIGMA_DATA_DIR).","Le service Windows et l'installateur commercial sont produits séparément.","","SHA-256 (SIGMA-Server.exe): $Hash") | Set-Content -Encoding UTF8 (Join-Path $PortableApp "LISEZ-MOI-PORTABLE.txt")
    $Zip = Join-Path $Portable "SIGMA-$Version-Windows-Portable.zip"
    if (Test-Path $Zip) { Remove-Item $Zip -Force }
    Compress-Archive -Path $PortableApp -DestinationPath $Zip -CompressionLevel Optimal

    if (-not $SkipInstaller) {
        Write-Host "[7/8] Installateur Inno Setup..." -ForegroundColor Green
        $ISCC = Ensure-InnoSetup
        Run $ISCC @((Join-Path $Root "installer\SIGMA-Setup.iss"))
        $SetupExe = Join-Path $ReleaseDir "SIGMA-$Version-Setup.exe"
        if (-not (Test-Path $SetupExe)) { Fail "Installateur absent après Inno Setup." }
        $SetupHash=(Get-FileHash -Algorithm SHA256 $SetupExe).Hash.ToLowerInvariant()
        Set-Content -Encoding ASCII -Path (Join-Path $ReleaseDir "SIGMA-$Version-Setup.sha256") -Value "$SetupHash  $(Split-Path -Leaf $SetupExe)"
    } else { Write-Host "[7/8] Installateur ignoré explicitement." -ForegroundColor Yellow }

    Write-Host "[8/8] Qualification du paquet..." -ForegroundColor Green
    $Manifest = [ordered]@{ product="SIGMA"; version=$Version; built_at=(Get-Date).ToString("o"); package="onedir"; exe=(Split-Path -Leaf $FinalExe); exe_sha256=$Hash; tests_skipped=[bool]$SkipTests; installer_skipped=[bool]$SkipInstaller }
    $Manifest | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Portable "BUILD-MANIFEST.json")
    $Ok=$true
    $Message="BUILD SIGMA $Version TERMINÉ.`n`nDossier autonome : $PortableApp`nZIP : $Zip`n`nInstallateur : $ReleaseDir`n`nJournal : $Log"
} catch {
    $Message="ÉCHEC DU BUILD SIGMA.`n`n$($_.Exception.Message)`n`nJournal : $Log"
    Write-Error $Message
    $Ok=$false
} finally {
    try { Stop-Transcript | Out-Null } catch { }
}
Show-Result $Ok $Message
if (-not $Ok) { exit 1 }
exit 0
