"""Moteur de préparation des bulletins SIGMA v1.4.

Le moteur ne fixe pas de modèle ministériel : il assemble uniquement les
résultats validés et les éléments de configuration du référentiel actif.
"""
from app.services.evaluation_engine import calculate_period_results

FINAL_STATES = {"validated", "locked", "published"}


def build_bulletin(rows: list[dict], db, framework_id: int, language: str = "fr", student=None, class_name: str | None = None) -> dict:
    """Prépare une synthèse exploitable par l'UI, l'API et les générateurs PDF.

    Les résultats non validés sont exclus pour éviter qu'un bulletin publié
    puisse dépendre d'une saisie encore en brouillon/soumission.
    """
    eligible = [r for r in rows if r.get("state") in FINAL_STATES]
    calc = calculate_period_results(eligible, db, framework_id, language)
    calc["student"] = {"id": student.id, "matricule": student.matricule, "last_name": student.last_name, "first_name": student.first_name} if student else None
    calc["class_name"] = class_name
    calc["eligible_results"] = len(eligible)
    calc["excluded_results"] = len(rows) - len(eligible)
    calc["ready"] = bool(eligible)
    return calc
