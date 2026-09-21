# Gate de livraison SIGMA

Depuis V4.27, la commande de référence est:

```bash
python scripts/release_gate.py
```

Le gate doit être exécuté dans un environnement où `requirements.txt` a été
installé **sans mocks ni shims**. Un échec de dépendance est bloquant.
