# SIGMA V4.32 — Windows Qualification

## Vérifié automatiquement
- script PowerShell protégé contre l'absence de PyInstaller et les codes de sortie non nuls ;
- vérification de la production de `SIGMA-Server.exe` ;
- installateur Inno Setup qui exécute `--setup` avant la création du service ;
- service `SIGMAPrimaireServer` configuré en démarrage automatique ;
- données persistantes sous `%PROGRAMDATA%\SIGMA` ;
- gestion STOP/SHUTDOWN du service ;
- build PyInstaller sans console et sans UPX.

## Non certifié ici
Ce conteneur n'est pas Windows et ne fournit ni Inno Setup, ni PyInstaller Windows, ni SCM Windows. La compilation réelle de l'EXE, l'installation MSI/Setup, le démarrage du service et le redémarrage d'une machine Windows restent donc des tests environnementaux obligatoires.

## Critère de sortie
Aucune certification commerciale Windows ne doit être déclarée tant que le script `build_windows.ps1`, `SIGMA-Setup.iss` et le service n'ont pas été exécutés sur une machine Windows propre.
