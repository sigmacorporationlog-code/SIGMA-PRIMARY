from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.evaluation import RatingScale, AppreciationRule, EvaluationFramework

FINAL_RESULT_STATES = {"validated", "locked", "published"}
SCORE_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.01")


def to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def round_score(value):
    if value is None:
        return None
    return to_decimal(value).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


def round_percent(value):
    if value is None:
        return None
    return to_decimal(value).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def rating_for_score(db: Session, framework_id: int, score, max_score, *, scales: list[RatingScale] | None = None):
    score_d, max_d = to_decimal(score), to_decimal(max_score)
    if score is None or max_d <= 0:
        return None
    pct = round_percent((score_d / max_d) * Decimal("100"))
    if scales is None:
        scales = db.query(RatingScale).filter(RatingScale.framework_id == framework_id).order_by(RatingScale.display_order).all()
    for scale in scales:
        if (scale.min_percent is None or pct >= to_decimal(scale.min_percent)) and (scale.max_percent is None or pct <= to_decimal(scale.max_percent)):
            return scale.code
    return None


def _scale_for_percent(scales: list[RatingScale], percent):
    if percent is None:
        return None
    p = to_decimal(percent)
    for scale in scales:
        if (scale.min_percent is None or p >= to_decimal(scale.min_percent)) and (scale.max_percent is None or p <= to_decimal(scale.max_percent)):
            return scale
    return None


def summarize(results: list[dict]):
    numeric = [r for r in results if r.get("score") is not None and r.get("max_score")]
    if not numeric:
        return {"average": None, "count": 0}
    total_weight = sum((to_decimal(r.get("coefficient") or 1) for r in numeric), Decimal("0"))
    weighted = sum(((to_decimal(r["score"]) / to_decimal(r["max_score"]) * Decimal("20")) * to_decimal(r.get("coefficient") or 1) for r in numeric), Decimal("0"))
    return {"average": round_score(weighted / total_weight) if total_weight else None, "count": len(numeric)}


EVALUATION_STATES = ("draft", "submitted", "checked", "validated", "locked", "published")
_STATE_ORDER = {state: i for i, state in enumerate(EVALUATION_STATES)}


def transition_state(current: str, target: str) -> bool:
    if current not in _STATE_ORDER or target not in _STATE_ORDER:
        return False
    return _STATE_ORDER[target] == _STATE_ORDER[current] + 1


def appreciation_for_percent(db: Session, framework_id: int, percent, language: str = "fr", *, rules: list[AppreciationRule] | None = None):
    if percent is None:
        return None
    p = to_decimal(percent)
    if rules is None:
        rules = (db.query(AppreciationRule)
                 .filter(AppreciationRule.framework_id == framework_id, AppreciationRule.active.is_(True))
                 .order_by(AppreciationRule.priority, AppreciationRule.id).all())
    for rule in rules:
        if (rule.min_percent is None or p >= to_decimal(rule.min_percent)) and (rule.max_percent is None or p <= to_decimal(rule.max_percent)):
            return {"code": rule.code, "text": rule.text_en if language == "en" else rule.text_fr}
    return None


def _subject_grade_point(bucket, scales):
    scale = _scale_for_percent(scales, bucket["percent"])
    bucket["grade"] = scale.code if scale else None
    bucket["grade_point"] = scale.grade_point if scale and scale.grade_point is not None else None
    return scale


def _gpa_for_mode(mode: str, overall_scale, subjects):
    if mode == "subject_weighted":
        points = [(to_decimal(b["grade_point"]), to_decimal(b.get("weight") or 0)) for b in subjects if b.get("grade_point") is not None and to_decimal(b.get("weight") or 0) > 0]
        total_weight = sum((w for _, w in points), Decimal("0"))
        if total_weight:
            return (sum((p*w for p,w in points), Decimal("0")) / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return overall_scale.grade_point if overall_scale and overall_scale.grade_point is not None else None


def calculate_period_results(rows: list[dict], db: Session, framework_id: int, language: str = "fr"):
    final_rows = [r for r in rows if "state" not in r or r.get("state") in FINAL_RESULT_STATES]
    usable = [r for r in final_rows if not r.get("is_absent") and r.get("score") is not None and r.get("max_score")]
    summary = summarize(usable)
    framework = db.get(EvaluationFramework, framework_id)
    gpa_mode = (framework.gpa_mode if framework and getattr(framework, "gpa_mode", None) else "overall_scale")
    scales = db.query(RatingScale).filter(RatingScale.framework_id == framework_id).order_by(RatingScale.display_order).all()
    rules = (db.query(AppreciationRule)
              .filter(AppreciationRule.framework_id == framework_id, AppreciationRule.active.is_(True))
              .order_by(AppreciationRule.priority, AppreciationRule.id).all())
    percent = round_percent(summary["average"] * Decimal("5")) if summary["average"] is not None else None
    subjects = {}
    competencies = {}
    for r in usable:
        pct20 = to_decimal(r["score"]) / to_decimal(r["max_score"]) * Decimal("20")
        weight = to_decimal(r.get("coefficient") or 1)
        if r.get("subject_id") is not None:
            key = r["subject_id"]
            bucket = subjects.setdefault(key, {"subject_id": key, "subject_name": r.get("subject_name") or "—", "weighted": Decimal("0"), "weight": Decimal("0"), "count": 0})
            bucket["weighted"] += pct20 * weight; bucket["weight"] += weight; bucket["count"] += 1
        if r.get("competency_id") is not None:
            key = r["competency_id"]
            bucket = competencies.setdefault(key, {"competency_id": key, "competency_name": r.get("competency_name") or "—", "weighted": Decimal("0"), "weight": Decimal("0"), "count": 0})
            bucket["weighted"] += pct20 * weight; bucket["weight"] += weight; bucket["count"] += 1
    for bucket in subjects.values():
        bucket["average"] = round_score(bucket["weighted"] / bucket["weight"]) if bucket["weight"] else None
        bucket["percent"] = round_percent(bucket["average"] * Decimal("5")) if bucket["average"] is not None else None
        _subject_grade_point(bucket, scales)
        bucket["appreciation"] = appreciation_for_percent(db, framework_id, bucket["percent"], language, rules=rules)
        bucket["weighted"] = None
        # keep weight temporarily for subject_weighted GPA
    subject_gpa = _gpa_for_mode(gpa_mode, None, list(subjects.values()))
    for bucket in subjects.values():
        del bucket["weighted"]
        del bucket["weight"]
    for bucket in competencies.values():
        bucket["average"] = round_score(bucket["weighted"] / bucket["weight"]) if bucket["weight"] else None
        bucket["percent"] = round_percent(bucket["average"] * Decimal("5")) if bucket["average"] is not None else None
        _subject_grade_point(bucket, scales)
        bucket["appreciation"] = appreciation_for_percent(db, framework_id, bucket["percent"], language, rules=rules)
        del bucket["weighted"]; del bucket["weight"]
    overall_scale = _scale_for_percent(scales, percent)
    gpa = subject_gpa if gpa_mode == "subject_weighted" and subject_gpa is not None else (overall_scale.grade_point if overall_scale and overall_scale.grade_point is not None else None)
    return {"average": summary["average"], "percent": percent, "count": summary["count"],
            "grade": overall_scale.code if overall_scale else None,
            "gpa": gpa,
            "gpa_mode": gpa_mode,
            "appreciation": appreciation_for_percent(db, framework_id, percent, language, rules=rules),
            "subjects": sorted(subjects.values(), key=lambda x: x["subject_name"]),
            "competencies": sorted(competencies.values(), key=lambda x: x["competency_name"])}
