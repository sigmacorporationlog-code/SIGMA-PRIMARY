# SIGMA Primaire — Release 2.23.0

## Déploiement Windows durci

- Version applicative `2.23.0-primary-commercial`.
- Script `build_windows.ps1` pour une construction reproductible sur Windows.
- Installation des dépendances puis tests et compilation Python avant PyInstaller.
- Vérification explicite de la présence de `SIGMA-Server.exe`.
- Génération de l'installateur Inno Setup si `ISCC.exe` est disponible.
- PyInstaller configuré sans UPX par défaut afin de réduire les échecs liés à l'absence de UPX.
- Le service Windows reste lancé via `SIGMA-Server.exe --service`.

## Limitation de validation

La compilation Windows et l'exécution du Gestionnaire de services Windows doivent être exécutées sur une machine Windows. Le script refuse de lancer la phase Windows depuis un autre OS.
