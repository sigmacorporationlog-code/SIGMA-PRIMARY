# SIGMA V4.13 — AI Multimodal Knowledge

## Objectif
Étendre la base documentaire SIGMA AI à l'ingestion directe de **TXT, Markdown, PDF et DOCX**, avec provenance des passages, activation/archivage des versions et citations plus précises.

## Sécurité
- Cloisonnement `school_id` obligatoire.
- Taille upload maximale : 15 Mo.
- Formats limités à TXT/MD/PDF/DOCX.
- Le binaire original n'est pas conservé par le moteur RAG.
- PDF scanné sans couche texte : refus explicite, OCR à prévoir dans une version dédiée.
- Contenu documentaire non transmis à un fournisseur externe par défaut (`AI_ALLOW_KNOWLEDGE_TO_PROVIDER=false`).

## Exploitation
`POST /api/ai/knowledge/documents/upload` accepte multipart/form-data.
`POST /api/ai/knowledge/documents/{id}/state` active ou archive une version.

L'activation d'une version désactive les autres documents portant le même titre dans le même établissement, sans supprimer l'historique.

## Dépendances
- `pypdf` pour PDF.
- `python-docx` pour DOCX.

## Limite assumée
Il s'agit d'une ingestion documentaire multimodale au sens des formats bureautiques/documentaires. L'OCR d'images et de PDF scannés reste une étape ultérieure, à traiter avec un composant OCR local et une politique de confidentialité dédiée.
