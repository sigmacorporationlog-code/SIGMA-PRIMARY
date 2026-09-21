@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Lanceur silencieux : aucune commande n'est demandee a l'utilisateur.
%SystemRoot%\System32\wscript.exe "%~dp0BUILD_SIGMA_WINDOWS.vbs"
exit /b %errorlevel%
