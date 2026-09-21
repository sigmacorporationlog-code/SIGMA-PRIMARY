from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.academic import ReportCard
from app.models.finance import Payment, Receipt
from app.models.organization import AcademicPeriod, AcademicYear, School
from app.models.students import SchoolClass, Student
from app.services.document_verification import decode_document_token
from app.services.rate_limit import RateLimitExceeded, limiter

router = APIRouter(prefix="/api/public/documents", tags=["Vérification publique"])


def _rate_limit(request: Request) -> None:
    host = request.client.host if request.client else "unknown"
    try:
        limiter.check(f"document-verify:{host}", limit=120, window_seconds=60)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="Trop de vérifications. Réessayez plus tard.") from exc


@router.get("/verify/{token}")
def verify_document(token: str, request: Request, db: Session = Depends(get_db)):
    """Vérifie un QR de bulletin/reçu sans exposer les données personnelles de l'élève."""
    _rate_limit(request)
    payload = decode_document_token(token)
    if payload is None:
        raise HTTPException(status_code=404, detail="Document introuvable ou jeton invalide")

    school_id = int(payload["school_id"])
    document_id = int(payload["sub"])
    document_type = payload["document_type"]

    if document_type == "bulletin":
        card = db.get(ReportCard, document_id)
        if card is None or not card.is_published:
            raise HTTPException(status_code=404, detail="Bulletin non publié ou introuvable")
        cls = db.get(SchoolClass, card.class_id)
        if cls is None or cls.school_id != school_id:
            raise HTTPException(status_code=404, detail="Document introuvable")
        school = db.get(School, cls.school_id)
        period = db.get(AcademicPeriod, card.academic_period_id)
        year = db.get(AcademicYear, period.academic_year_id) if period else None
        return JSONResponse({
            "valid": True,
            "document_type": "bulletin",
            "school_name": school.name if school else "SIGMA",
            "class_name": cls.name,
            "academic_year": year.label if year else None,
            "period": period.name if period else None,
            "published": True,
        }, headers={"Cache-Control": "no-store"})

    receipt = db.get(Receipt, document_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    payment = db.get(Payment, receipt.payment_id)
    if payment is None or payment.is_cancelled:
        raise HTTPException(status_code=404, detail="Reçu annulé ou introuvable")
    student = db.get(Student, payment.student_id)
    if student is None or student.school_id != school_id:
        raise HTTPException(status_code=404, detail="Document introuvable")
    school = db.get(School, student.school_id)
    return JSONResponse({
        "valid": True,
        "document_type": "receipt",
        "school_name": school.name if school else "SIGMA",
        "receipt_number": receipt.receipt_number,
        "paid_at": payment.paid_at.isoformat(),
        "cancelled": False,
    }, headers={"Cache-Control": "no-store"})
