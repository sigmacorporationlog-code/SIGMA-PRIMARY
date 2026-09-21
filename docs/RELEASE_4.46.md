# SIGMA V4.46 — Hardening, récupération de compte, matricules et photos

## Objectif
V4.46 est une phase de durcissement avant certification commerciale. Elle privilégie les mécanismes réellement exploitables et testables plutôt que l'ajout de nouveaux modules.

## Sécurité des comptes
- Mot de passe nouveau : 15 à 128 caractères, Unicode accepté.
- Les nouveaux hashes utilisent le mot de passe complet via SHA-256 avant bcrypt; les anciens hashes bcrypt restent compatibles et sont modernisés après une connexion réussie.
- Changement de mot de passe authentifié.
- Réinitialisation administrateur avec révocation immédiate des sessions et option de changement obligatoire.
- Récupération autonome par email via jeton aléatoire à usage unique, hashé en base et expirant.
- Réponse uniforme de la demande « mot de passe oublié » pour éviter l'énumération de comptes.
- Compte administrateur initial marqué `must_change_password`.
- Le token d'accès web n'est plus conservé dans `localStorage`; le refresh token web est placé dans un cookie HttpOnly.

## Matricules
- Génération automatique si le matricule est laissé vide.
- Stratégies : séquence, année+séquence, année+niveau+séquence, établissement+année+séquence, ou format personnalisé.
- Format personnalisable avec `{SEQ}`, `{SEQ:05}`, `{YY}`, `{YYYY}`, `{LEVEL}`, `{STREAM}`, `{SCHOOL}`, `{CAMPUS}`.
- Séquence incrémentée par mise à jour SQL atomique; aucune logique `count()+1`.
- Contrainte d'unicité établissement + matricule conservée comme barrière finale.
- Aperçu de matricule sans consommation de séquence.

## Photos élèves
- Recadrage interactif carré dans l'interface : déplacement + zoom.
- Export normalisé en JPEG 600×600.
- Correction de l'orientation EXIF.
- Limite de pixels pour réduire le risque de décompression abusive.
- Échec fermé si Pillow n'est pas disponible.

## Migration
- `20260916_5400_auth_recovery.py`
- `20260916_5500_matricule_config.py`
- Upgrade complet et downgrade complet testés sur SQLite.

## Limites encore ouvertes
- Le reset email nécessite une configuration SMTP réelle.
- La certification bcrypt/python-jose, Windows/PyInstaller, PostgreSQL serveur et Android SDK doit être réalisée dans les environnements correspondants.
- La protection XSS doit encore être généralisée à toutes les vues dynamiques; V4.46 supprime déjà le stockage persistant du JWT web, mais ce chantier n'est pas considéré terminé tant que le scan des sinks HTML n'est pas propre.


## H2 — production precision and concurrency hardening

- Montants financiers stockés en `NUMERIC(14,2)` au lieu de `FLOAT`.
- Paiements protégés contre le double-débit concurrent par verrouillage de facture.
- Clé d’idempotence optionnelle sur la création de paiement pour supporter les retries offline/mobile.
- Moyennes et classements du moteur académique limités aux notes validées/verrouillées/publiées.
- Rate limiting partagé Redis disponible via `RATE_LIMIT_REDIS_URL`, avec repli local explicite.
- `create_all()` limité aux environnements de bootstrap non production ; les schémas de production passent par Alembic.
- Téléchargements Android déposés dans le stockage privé de l’application plutôt que dans le dossier public partagé.
## H2 — Production hardening complémentaire

- Monnaie: `Decimal/NUMERIC(14,2)` pour les flux financiers et migration Alembic `20260920_6100`.
- Paiements: clé d'idempotence unique + verrou de facture + gestion de concurrence.
- Académique: seuls `validated/locked/published` alimentent les calculs finaux; barèmes/règles chargés par lot.
- Classe/période: lectures groupées des élèves/résultats, réduction N+1 sur les espaces à fort volume.
- Rate limiting: backend Redis partagé optionnel via `RATE_LIMIT_REDIS_URL`, repli local journalisé.
- Readiness: contrôle explicite de l'alignement Alembic application/base.
- Android: téléchargement documentaire vers stockage externe privé de l'application et logs des échecs.
- Release gate: validation du driver PostgreSQL/Redis et round-trip de migration `6100 -> 5900 -> 6100`.

