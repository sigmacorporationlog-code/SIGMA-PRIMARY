# PYTHON FULL TEST REPORT

## Resultat final exécutable

`pytest -q --continue-on-collection-errors`

**468 PASS / 3 FAIL / 1 ERROR / 3 warnings**

Total de résultats finaux : **472**.

### Échecs

1. `tests/test_v457d_first_run_admin_password.py::test_first_run_admin_has_known_password_and_forced_change_blocks_access`
2. `tests/test_v467_direction_profile_student_rights.py::test_bootstrapped_director_can_create_students`
3. `tests/test_v468_cloud_backup_providers.py::test_sync_isolates_failures_and_never_raises`

Les trois échecs terminent sur `ModuleNotFoundError: No module named 'jose'` lors du bootstrap.

### Erreur de collecte

`tests/test_v446_correction_actions.py` ne peut pas être collecté pour la même dépendance manquante `python-jose`.

### Avertissements

3 avertissements de dépréciation Pydantic concernant `json_encoders` dans `tests/test_p2_p3_data_validation.py`.

### Périmètre ciblé

La batterie P2/P3 + sécurité + backup/offline exécutée séparément a obtenu : **156 PASS / 2 FAIL**, les deux échecs étant également causés par `python-jose`.

Le contrôle sécurité/i18n/versionnement/statique séparé a obtenu **17/17 PASS**.

Le cycle backup ciblé après correction a obtenu **12/12 PASS**.
