# SIGMA V4.9 — AI Action Center

V4.9 ajoute un centre de propositions d'actions IA auditable.

## Principe

L'IA peut analyser et proposer. Elle ne peut pas exécuter une action sensible automatiquement.

Flux : `Analyse → Proposition → Validation humaine → futur exécuteur spécialisé`.

## Types de propositions

- `communication_draft`
- `finance_reminder`
- `pedagogy_remediation`
- `report_generation`

Les propositions expirent par défaut après 60 minutes et au maximum après 7 jours.

## Sécurité

- permission `administration.ai.use` ;
- contrôle `school_id` ;
- audit des créations/validations/rejets ;
- payload conservé pour permettre la revue humaine ;
- aucune route d'exécution dans V4.9 ;
- une proposition approuvée n'entraîne donc aucun envoi, paiement, modification ou suppression.
