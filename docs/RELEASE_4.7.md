# SIGMA V4.7 — AI Foundation

SIGMA Intelligence introduit une passerelle IA contrôlée. Le modèle externe ne dispose jamais d'un accès SQL direct : les données sont exposées par des outils SIGMA bornés à l'établissement de l'utilisateur.

## Sécurité
- Permission dédiée : `administration.ai.use`.
- Outil initial en lecture seule : `school_insight`.
- Journalisation minimale des interactions : hash du prompt, fournisseur, outil, statut, latence.
- Le prompt brut n'est pas conservé dans `ai_interactions`.
- Les identifiants directs des élèves sont retirés avant transmission à un fournisseur externe, sauf activation explicite de `AI_ALLOW_PERSONAL_DATA_TO_PROVIDER=true`.
- Aucune action d'écriture n'est disponible en V4.7.
- L'IA n'est pas un outil de diagnostic médical, psychologique ou social.

## Fournisseurs
`AI_PROVIDER=disabled` par défaut.

Options :
- `disabled` : aucune interaction IA.
- `local` : fallback déterministe hors connexion, utile pour tester le cockpit sans fournisseur externe.
- `openai_compatible` : endpoint compatible Chat Completions configurable par `AI_BASE_URL`, `AI_API_KEY` et `AI_MODEL`.

## API
- `GET /api/ai/status`
- `POST /api/ai/ask`

V4.7 est une fondation. Les outils Finance, Pédagogie, Communication et Documents seront ajoutés après validation des politiques de confidentialité et d'autorisation.
