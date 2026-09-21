# SIGMA V4.12 — AI Knowledge / RAG

## Objet

V4.12 ajoute une base documentaire institutionnelle pour SIGMA Intelligence. Les documents sont découpés en fragments, hachés, indexés et recherchables sans service vectoriel externe.

## Sécurité

- Chaque document et chaque fragment portent le `school_id`.
- Les recherches sont strictement bornées au périmètre de l'utilisateur.
- Le contenu documentaire n'est pas transmis à un fournisseur IA externe par défaut (`AI_ALLOW_KNOWLEDGE_TO_PROVIDER=false`).
- La transmission du contenu documentaire et la transmission de données personnelles sont deux autorisations techniques distinctes.
- Les réponses peuvent citer le titre, la version et le fragment source.

## API

- `POST /api/ai/knowledge/documents` : indexer un document texte.
- `GET /api/ai/knowledge/documents` : lister les documents du périmètre.
- `POST /api/ai/knowledge/search` : recherche documentaire avec citations.
- `POST /api/ai/ask` : le Copilot enrichit son contexte avec les sources documentaires pertinentes.

## Limites V4.12

L'indexation est actuellement textuelle et déterministe. Les imports PDF/DOCX, embeddings vectoriels, OCR et gestion avancée des versions documentaires sont volontairement réservés à une étape ultérieure.

## Validation

- Suite de tests : 167 tests réussis.
- Compilation Python : OK.
- Migration SQLite jusqu'à `20260915_4600` : OK.
