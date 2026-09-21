# SIGMA V4.26 — Rapport d'audit sécurité & pré-production

## 1. Objectif

V4.26 ne constitue pas une simple évolution fonctionnelle. Cette version vise à transformer les contrôles identifiés en V4.25 en critères vérifiables avant commercialisation.

## 2. Résultats automatisés

| Contrôle | Résultat |
|---|---:|
| Suite de régression SIGMA | **206 passed** |
| Compilation `app` + `alembic` | **OK** |
| Import de tous les modules `app.api` | **OK** |
| Migration fraîche `alembic upgrade head` SQLite | **OK** |
| Downgrade complet `head -> base` SQLite | **OK** |
| Upgrade d'une base V4.25 simulée `5100 -> 5200` | **OK** |
| Comparaison ORM / schéma migré | **82/82 tables ORM présentes** |
| Contrôles tenant étudiant | **OK** |
| Contrôles tenant académique | **OK** |
| Contrôles tenant finance | **OK** |
| Protection chemin média traversal | **OK** |
| Révocation JWT par `token_version` | **OK** |
| Refresh JWT avec `sub` malformé | **OK** |

## 3. Correctifs apportés

### 3.1 Alembic

Une vraie migration initiale `20260913_1600_initial_core.py` a été introduite. La chaîne ne dépend plus implicitement de `Base.metadata.create_all()` pour disposer des tables historiques `schools` et `users`.

La migration V4.25 `20260915_5200_auth_token_version.py` utilise le batch mode Alembic afin de rester compatible avec SQLite.

Le test de migration fraîche a parcouru toute la chaîne jusqu'à `20260915_5200`, puis le downgrade complet jusqu'à `base`.

### 3.2 Isolation multi-tenant

Contrôles renforcés notamment sur :

- changement de statut d'un élève ;
- retrait d'un élève ;
- photos élèves ;
- liste des élèves d'une classe ;
- inscriptions ;
- moyennes et classements ;
- bulletins et exports PDF ;
- reçus de paiement et exports PDF.

### 3.3 Fichiers

`resolve_media_path()` vérifie désormais que le chemin résolu reste strictement sous `MEDIA_ROOT`, empêchant une traversée de répertoires via un chemin stocké ou manipulé de manière malveillante.

### 3.4 Authentification

Le refresh JWT rejette désormais proprement un `sub` absent ou non numérique au lieu de provoquer une erreur serveur.

La révocation par `token_version` reste appliquée côté serveur.

### 3.5 Cohérence applicative

L'audit d'import de tous les modules `app.api` a découvert deux problèmes qui n'étaient pas couverts par la suite précédente :

- `EnrollmentCreate` manquait dans les imports de `students.py` ;
- `governance_control_plane` était importé mais absent de `services/cloud.py`.

Les deux ont été corrigés.

## 4. Tests de non-régression sécurité

Le fichier `tests/test_v4_25_security.py` couvre notamment les scénarios d'accès inter-établissements sur deux tenants distincts.

Les tests vérifient non seulement le code HTTP attendu, mais également l'absence de mutation de la donnée protégée lorsqu'un accès inter-tenant est tenté.

## 5. Limitation de l'environnement d'audit

L'image d'exécution utilisée pour cet audit ne contient pas les wheels `bcrypt` et `python-jose`, bien qu'ils soient déclarés dans `requirements.txt` du produit.

Les tests d'import et les tests JWT ont donc utilisé un shim de test pour isoler la logique SIGMA. Cela ne remplace pas une validation d'intégration avec les versions réelles des dépendances. Cette validation doit être effectuée dans le pipeline de build Windows/production qui installe intégralement `requirements.txt`.

## 6. Conclusion

**V4.26 est validée fonctionnellement pour le périmètre testé.**

Elle peut servir de base de Release Candidate, sous réserve de l'exécution finale dans un environnement Windows propre avec toutes les dépendances réelles et d'un test de restauration sur une machine distincte.
