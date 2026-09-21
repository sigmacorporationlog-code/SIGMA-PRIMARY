# SIGMA V4.41 — Automatic Update Agent

## Objectif

V4.41 ajoute un agent de mise à jour automatique à activation contrôlée. Il ne remplace jamais un exécutable sans validation préalable de la taille et du SHA-256 de l'artefact.

## Flux

1. Lire un manifeste JSON.
2. Vérifier version, canal, URL, taille et SHA-256.
3. Déterminer si une version plus récente est disponible.
4. Acquérir un verrou local pour éviter deux mises à jour concurrentes.
5. Télécharger vers un fichier temporaire.
6. Vérifier la taille exacte et le SHA-256.
7. Renommer atomiquement l'artefact vérifié.
8. Sur Windows uniquement, si `--activate` est explicitement demandé, déléguer à `deployment_guard` : arrêt contrôlé, remplacement, démarrage, health-check et rollback.

## Sécurité par défaut

`UPDATE_ENABLED=false`. Le simple téléchargement n'active pas le serveur. L'activation exige explicitement `--activate` et reste soumise aux garde-fous Windows existants.

## Manifeste

`python scripts/generate_update_manifest.py SIGMA-Server.exe --version 4.41.0 --url https://updates.example/SIGMA-Server.exe --output update-manifest.json`

Le manifeste contient la taille et le SHA-256 calculés sur l'artefact réel.

## Limites

Le protocole ne constitue pas à lui seul une signature cryptographique d'éditeur. Pour une chaîne de distribution Internet de niveau entreprise, le prochain durcissement doit ajouter une signature asymétrique du manifeste avec clé privée hors machine et vérification par clé publique embarquée.

La certification Windows réelle et le test de rollback doivent être exécutés sur Windows Server réel.
