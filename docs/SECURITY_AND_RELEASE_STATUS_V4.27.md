# SIGMA V4.27 — État de certification

## Tests disponibles dans l'environnement de développement

**206/206 tests automatisés PASS** au moment de la création du package.

- 206 tests: PASS.
- Compilation Python: PASS.
- Cycle Alembic SQLite vierge `upgrade head`: PASS.
- Cycle Alembic `downgrade base`: PASS.

## Blocage de certification runtime

L'environnement d'audit utilisé pour cette livraison ne fournit pas `bcrypt`
et ne permet pas d'installer les dépendances depuis Internet. La suite
portable utilise donc des shims uniquement dans les tests historiques V4.25
pour permettre l'analyse statique et la régression hors runtime complet.

**Conséquence:** la certification finale de l'authentification doit être faite
avec les vraies dépendances déclarées dans `requirements.txt`, via
`scripts/release_gate.py`.

Cette limitation est volontairement classée **BLOCKER de recette**, et non
comme PASS implicite.
