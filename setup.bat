@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ==============================================
echo   SIGMA - Installation / preparation pilote
echo ==============================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Python Launcher (py) est introuvable.
  echo Pour une installation commerciale, utilisez SIGMA-Setup.exe.
  exit /b 10
)

py -c "import sys; v=sys.version_info; raise SystemExit(0 if (v.major==3 and 11<=v.minor<=14) else 1)"
if errorlevel 1 (
  echo [ERREUR] SIGMA exige Python 3.11, 3.12, 3.13 ou 3.14.
  py --version
  exit /b 11
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/6] Creation de l'environnement virtuel...
  py -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [1/6] Environnement virtuel deja present.
)

set "PY=.venv\Scripts\python.exe"

 echo [2/6] Mise a jour de pip...
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/6] Installation des dependances SIGMA...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [4/6] Preparation de la configuration locale...
"%PY%" run_server.py --setup
if errorlevel 1 goto :fail

echo [5/6] Application des migrations de base de donnees...
"%PY%" -m alembic upgrade head
if errorlevel 1 goto :fail

echo [6/6] Verification finale de l'application...
"%PY%" -c "from app.main import app; print('SIGMA OK - routes:', len(app.routes))"
if errorlevel 1 goto :fail

echo.
echo Installation pilote technique terminee.
echo Pour le produit sans terminal, utilisez SIGMA-Setup.exe.
echo.
exit /b 0

:fail
echo.
echo [ERREUR] L'installation SIGMA a echoue. Code=%errorlevel%
echo Verifiez la connexion Internet et le journal affiche ci-dessus.
exit /b %errorlevel%
