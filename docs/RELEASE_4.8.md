# SIGMA V4.8 — AI Copilot

V4.8 étend SIGMA Intelligence avec des outils IA spécialisés en lecture seule.

## Outils
- `school_insight`
- `finance_insight`
- `attendance_insight`
- `class_risk_snapshot`
- `student_360`

## Sécurité
- périmètre établissement dérivé de l'utilisateur ;
- contrôle de `school_id` sur élève et classe ;
- aucun accès SQL direct du fournisseur IA ;
- données personnelles supprimées avant envoi à un fournisseur externe lorsque `AI_ALLOW_PERSONAL_DATA_TO_PROVIDER=false` ;
- aucune action d'écriture exposée ;
- journalisation des interactions sans stockage du prompt brut.

## Limites
Les scores pédagogiques sont des indicateurs d'aide à la décision et non des diagnostics. Toute action sensible doit rester validée par un utilisateur habilité.
