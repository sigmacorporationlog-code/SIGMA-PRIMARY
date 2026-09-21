from io import BytesIO
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

GREEN = colors.HexColor("#11633A")


def generate_honor_board_pdf(school_name: str, period_name: str, rule_name: str, entries: list[dict], language: str = "fr") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=12 * mm, rightMargin=12 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("HonorTitle", parent=styles["Title"], textColor=GREEN, fontSize=16)
    sub = ParagraphStyle("HonorSub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    header = ["Rang", "Matricule", "Élève", "Classe", "Moyenne", "Abs. injustifiées"] if language != "en" else ["Rank", "ID", "Student", "Class", "Average", "Unjustified absences"]
    data = [header]
    for row in entries:
        data.append([
            row["rank"], row["matricule"], row["student_name"], row["class_name"], f'{row["score"]:.2f}/20', row.get("unjustified_absences", 0)
        ])
    elements = [Paragraph(school_name, title), Paragraph(f"{rule_name} — {period_name}", styles["Heading2"]), Paragraph(date.today().strftime("%d/%m/%Y"), sub), Spacer(1, 5 * mm)]
    table = Table(data, repeatRows=1, colWidths=[18*mm, 30*mm, 55*mm, 32*mm, 25*mm, 30*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), GREEN),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.35, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4F6F5")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
