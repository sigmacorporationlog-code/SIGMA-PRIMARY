# SIGMA 2.2.0 — Distribution multi-postes

Cette release ajoute les accusés de réception par appareil pour la distribution des opérations de synchronisation. Un poste ne reçoit plus ses propres opérations via `/api/sync/pull`, peut accuser réception des opérations reçues, et le serveur évite leur rediffusion lors des pulls ultérieurs.

La synchronisation reste transactionnelle et ne prétend pas encore résoudre automatiquement les conflits métier.
