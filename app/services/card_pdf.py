import io
import logging

logger = logging.getLogger(__name__)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from app.models.organization import School
from app.models.students import Student, ClassMembership, Guardian
from app.services.media import resolve_media_path
from app.services.badge_engine import secure_qr_payload

CARD_W = 90 * mm
CARD_H = 54 * mm
MARGIN_X = 10 * mm
MARGIN_Y = 6 * mm
GAP_X = 5 * mm
GAP_Y = 3 * mm


def _draw_card(c, db, card, x, y):
    school = db.get(School, card.school_id)
    student = db.get(Student, card.student_id)
    if not student:
        return
    m = db.query(ClassMembership).filter(ClassMembership.student_id == student.id, ClassMembership.left_at.is_(None)).order_by(ClassMembership.enrolled_at.desc()).first()
    cls = m.school_class.name if m and m.school_class else "—"
    primary = "#11633A"
    try:
        template = db.get(__import__('app.models.documents', fromlist=['CardTemplate']).CardTemplate, card.template_id)
        primary = (template.layout or {}).get("primary_color", primary) if template else primary
    except Exception as exc:
        logger.warning("Impossible de charger le modèle de carte %s: %s", card.template_id, exc)
    c.setStrokeColor(primary); c.roundRect(x, y, CARD_W, CARD_H, 4*mm, stroke=1, fill=0)
    c.setFillColor(primary); c.roundRect(x, y+CARD_H-13*mm, CARD_W, 13*mm, 4*mm, stroke=0, fill=1)
    c.rect(x, y+CARD_H-13*mm, CARD_W, 4*mm, stroke=0, fill=1)
    c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold", 8); c.drawString(x+4*mm, y+CARD_H-5*mm, (school.name if school else "SIGMA")[:34])
    c.setFont("Helvetica", 5.5); c.drawString(x+4*mm, y+CARD_H-9*mm, "CARTE SCOLAIRE")
    if student.photo_path and resolve_media_path(student.photo_path).exists():
        c.drawImage(ImageReader(str(resolve_media_path(student.photo_path))), x+4*mm, y+16*mm, 22*mm, 27*mm, preserveAspectRatio=True, anchor='c', mask='auto')
    c.setFillColorRGB(0,0,0); c.setFont("Helvetica-Bold", 9); c.drawString(x+30*mm, y+CARD_H-20*mm, f"{student.last_name} {student.first_name}"[:28])
    c.setFont("Helvetica", 6.5)
    lines = [f"Matricule : {student.matricule}", f"Classe : {cls}"]
    if student.birth_date: lines.append(f"Né(e) le : {student.birth_date.isoformat()}")
    for i, line in enumerate(lines): c.drawString(x+30*mm, y+CARD_H-(25+i*5)*mm, line[:30])
    c.setFont("Helvetica", 5.5); c.setFillColorRGB(.35,.35,.35); c.drawString(x+4*mm, y+7*mm, card.card_number[:25])
    c.setFont("Helvetica", 5); c.drawRightString(x+CARD_W-4*mm, y+7*mm, f"Statut: {card.status}")
    # Opaque QR payload: token only, never PII.
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=1); qr.add_data(secure_qr_payload(card.access_code)); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white"); buf=io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
        c.drawImage(ImageReader(buf), x+CARD_W-25*mm, y+14*mm, 20*mm, 20*mm, preserveAspectRatio=True, mask='auto')
    except ImportError:
        c.setFont("Helvetica", 5); c.drawRightString(x+CARD_W-4*mm, y+14*mm, "QR indisponible")


def generate_student_card_pdf(db, card):
    b=io.BytesIO(); c=canvas.Canvas(b,pagesize=A4)
    _draw_card(c, db, card, (A4[0]-CARD_W)/2, (A4[1]-CARD_H)/2)
    c.showPage(); c.save(); return b.getvalue()


def generate_class_cards_pdf(db, cards):
    b=io.BytesIO(); c=canvas.Canvas(b,pagesize=A4)
    xs=[MARGIN_X, MARGIN_X+CARD_W+GAP_X]; ys=[A4[1]-MARGIN_Y-CARD_H, A4[1]-MARGIN_Y-CARD_H*2-GAP_Y, A4[1]-MARGIN_Y-CARD_H*3-GAP_Y*2, A4[1]-MARGIN_Y-CARD_H*4-GAP_Y*3, A4[1]-MARGIN_Y-CARD_H*5-GAP_Y*4]
    for i, card in enumerate(cards):
        if i and i % 10 == 0: c.showPage()
        col=i%2; row=(i%10)//2
        _draw_card(c, db, card, xs[col], ys[row])
    c.showPage(); c.save(); return b.getvalue()
