# SIGMA V4.14 — AI Knowledge Governance & Hybrid Retrieval

## Objectif

Transformer la base documentaire SIGMA AI en véritable référentiel institutionnel gouverné : classement, tags, cycle de vie documentaire, approbation humaine et recherche hybride déterministe.

## Nouveautés

- statuts `draft`, `review`, `published`, `archived` ;
- dossiers documentaires et tags ;
- approbation et publication par utilisateur ;
- une seule version publiée/active par titre et établissement ;
- recherche pondérée type BM25/IDF avec bonus titre, tags et phrase exacte ;
- résultats limités aux documents publiés et actifs ;
- cloisonnement strict par `school_id` ;
- provenance page/paragraphe/unité conservée ;
- transmission du contenu à un fournisseur externe toujours désactivée par défaut.

## Migration

Migration `20260915_4800_ai_knowledge_governance.py`.

## Sécurité

La publication est une opération humaine explicite. Un document en brouillon ou en revue ne peut pas alimenter les réponses RAG. Les anciennes versions sont conservées pour traçabilité mais automatiquement archivées lors de la publication d'une nouvelle version du même titre.

## Limite assumée

Le retrieval reste déterministe et sans dépendance à un moteur vectoriel ou à un modèle d'embedding externe. Cela privilégie la stabilité, le mode offline et la confidentialité. Une couche vectorielle pourra être ajoutée ultérieurement comme accélérateur facultatif, sans remplacer ce moteur de secours.
