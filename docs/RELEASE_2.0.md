# SIGMA v2.0.0 — Identité offline et créations synchronisables

Cette version franchit une étape importante du mode offline/online : un poste peut maintenant produire une création d'élève ou de responsable avec un identifiant client stable, puis le serveur lui attribue un identifiant métier définitif.

## Garanties

- correspondance `client_entity_id` → `server_entity_id` persistée par établissement et type d'entité ;
- réémission d'une même identité client traitée de manière idempotente ;
- création d'élève contrôlée par le matricule ;
- création de responsable contrôlée par nom/prénom/téléphone lorsque le téléphone est fourni ;
- whitelist stricte des champs synchronisables ;
- transactions SQLAlchemy et `flush()` avant émission de l'identité serveur ;
- conflits explicites, jamais de fusion silencieuse ;
- les mises à jour et suppressions peuvent utiliser l'identifiant serveur ou l'identifiant client déjà enregistré ;
- les créations restent limitées à `Student` et `Guardian` dans cette première tranche.

## Limite volontaire

Les inscriptions (`ClassMembership`), notes, évaluations et bulletins ne sont pas encore créés offline par ce protocole. Ils seront activés après validation des invariants métier propres à chaque domaine.

## Architecture de stockage

Le serveur central reste l'autorité métier. Le client offline doit conserver sa file locale et son UUID métier jusqu'à réception de l'accusé serveur. Le protocole v2.0 ne demande jamais aux postes clients de partager directement le fichier SQLite du serveur.

Cette séparation est importante : SQLite WAL améliore la concurrence sur une machine, mais son mode WAL ne doit pas être utilisé comme mécanisme de partage d'un fichier de base via un système de fichiers réseau. La documentation SQLite précise que tous les processus d'une base WAL doivent être sur le même hôte. Le réseau SIGMA doit donc passer par l'API du serveur. 
