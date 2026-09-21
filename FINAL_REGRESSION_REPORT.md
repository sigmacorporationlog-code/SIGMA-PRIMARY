# FINAL REGRESSION REPORT

## Résultat final

**468 PASS / 3 FAIL / 1 ERROR / 3 warnings**.

### Régression introduite pendant cette qualification

Un défaut réel de backup a été découvert pendant le scénario d'intégration et corrigé. Après correction :

- backup/restore réel SQLite : PASS ;
- suite backup ciblée : 12/12 PASS ;
- suite globale : 468 PASS, 3 FAIL, 1 ERROR.

### Aucun nouveau défaut indépendant de `python-jose`

Les trois FAIL et l'ERROR restants sont attribués à la dépendance `python-jose` manquante. Ils ne sont pas classés comme régressions du code métier P2/P3.

### Statique

Sécurité/i18n/versionnement : **17/17 PASS**.
