# SIGMA Primaire 2.11.0

## Synchronisation multi-postes et conflits

Cette version consolide la synchronisation offline/online et ajoute la résolution explicite des conflits côté serveur.

- journal des conflits avec traçabilité de la résolution ;
- résolution `discard` ou `rebase` ;
- migration Alembic `20260913_2600` ;
- contrôle de version logique par entité ;
- conservation des opérations locales lors des coupures réseau ;
- tests de non-régression de la pile de synchronisation.

Les PDF et fichiers binaires restent soumis à la disponibilité du serveur.

## Vérification

Suite complète : 67 tests réussis.
Compilation Python : OK.
ZIP : testé avec `unzip -t`.
