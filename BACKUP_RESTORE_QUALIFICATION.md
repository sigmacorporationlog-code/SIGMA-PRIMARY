# BACKUP / RESTORE QUALIFICATION

**Status: PARTIAL — SQLite réel PASS**

Une base SQLite de qualification a été migrée jusqu'à `20260920_6340`, un marqueur transactionnel a été créé, puis :

1. backup réel ZIP créé ;
2. manifeste SHA-256 validé ;
3. base source modifiée après backup ;
4. restauration vers un répertoire isolé ;
5. marqueur restauré à sa valeur antérieure ;
6. `PRAGMA integrity_check` = `ok`.

Résultat : **BACKUP_RESTORE_REAL = PASS**.

### Défaut détecté et corrigé pendant qualification

`create_backup()` produisait un fichier temporaire suffixé `.tmp`, alors que `validate_backup()` exigeait `.zip`. Le backup échouait avant publication.

Correction appliquée : suffixe `.tmp.zip` afin de rester temporaire tout en satisfaisant le contrat de validation.

Régression ciblée après correction : **12/12 PASS**.

La sauvegarde/restauration PostgreSQL réelle reste BLOCKED tant qu'une instance PostgreSQL n'est pas disponible.
