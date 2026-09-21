# BROWSER E2E REPORT

**Status: BLOCKED — ENVIRONMENT POLICY**

Chromium système 144.0.7559.96 est présent et démarre.

Cependant, dans cette sandbox, les navigations Playwright vers `127.0.0.1` et `file://` sont bloquées avec `ERR_BLOCKED_BY_ADMINISTRATOR`. Le lancement CLI headless reste suspendu et termine en timeout.

Il est donc impossible de certifier les parcours complets connexion → dashboard → établissement → élève → photo → carte → tableau d'honneur → import/export → permissions → messages → logout.

Aucun résultat navigateur n'est transformé en PASS par approximation.
