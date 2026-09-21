"""
Moteur PDF de SIGMA (reportlab — pur Python, aucune dépendance système,
fiable à installer sur n'importe quel serveur d'établissement).

Deux générateurs pour cette première phase :
  - export d'une liste d'élèves en PDF (tableau simple, pour impression /
    archivage administratif) ;
  - bulletin (ReportCard) en PDF, avec le détail par matière, la moyenne
    générale, le rang, et l'appréciation — conforme au §23 du cahier des
    charges ("Export: PDF / impression / archivage").
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
)
from reportlab.lib.utils import ImageReader
import qrcode

BRAND_GREEN = colors.HexColor("#11633A")
BRAND_ORANGE = colors.HexColor("#FF8A00")

styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("SigmaTitle", parent=styles["Title"], textColor=BRAND_GREEN, fontSize=16)
SUBTITLE_STYLE = ParagraphStyle("SigmaSubtitle", parent=styles["Normal"], textColor=colors.grey, fontSize=10)
SECTION_STYLE = ParagraphStyle("SigmaSection", parent=styles["Heading2"], textColor=BRAND_GREEN, fontSize=12)




def _verification_qr_elements(verification_url: str | None, language: str = "fr"):
    if not verification_url:
        return []
    image = qrcode.make(verification_url)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    label = "Scan to verify authenticity" if language == "en" else "Scanner pour vérifier l'authenticité"
    return [
        Spacer(1, 4 * mm),
        Table([[ImageReader(stream), Paragraph(label, SUBTITLE_STYLE)]], colWidths=[30 * mm, 125 * mm], rowHeights=[26 * mm]),
    ]


def generate_students_list_pdf(school_name: str, students: list[dict]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)

    elements = [
        Paragraph(school_name, TITLE_STYLE),
        Paragraph(f"Liste des élèves — {len(students)} élève(s) — généré le {date.today().strftime('%d/%m/%Y')}", SUBTITLE_STYLE),
        Spacer(1, 10 * mm),
    ]

    table_data = [["Matricule", "Nom", "Prénom", "Classe", "Sexe", "Statut"]]
    for s in students:
        table_data.append([
            s.get("matricule", ""), s.get("last_name", ""), s.get("first_name", ""),
            s.get("class_name", "") or "—", s.get("sex", "") or "—", s.get("status", ""),
        ])

    table = Table(table_data, repeatRows=1, colWidths=[28 * mm, 35 * mm, 35 * mm, 25 * mm, 15 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


def generate_report_card_pdf(
    school_name: str,
    academic_year_label: str,
    period_name: str,
    student_full_name: str,
    student_matricule: str,
    class_name: str,
    subjects: list[dict],  # [{"subject_name", "average", "coefficient"}]
    general_average: float | None,
    class_rank: int | None,
    class_size: int | None,
    appreciation: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)

    elements = [
        Paragraph(school_name, TITLE_STYLE),
        Paragraph(f"Bulletin scolaire — {academic_year_label} — {period_name}", SUBTITLE_STYLE),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>{student_full_name}</b> — Matricule {student_matricule} — Classe {class_name}", styles["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph("Résultats par matière", SECTION_STYLE),
    ]

    table_data = [["Matière", "Moyenne / 20", "Coefficient"]]
    for subject in subjects:
        avg = subject.get("average")
        table_data.append([
            subject.get("subject_name", ""),
            f"{avg:.2f}" if avg is not None else "—",
            str(subject.get("coefficient", "")),
        ])

    table = Table(table_data, repeatRows=1, colWidths=[80 * mm, 40 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F5")]),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 8 * mm))

    summary_data = [
        ["Moyenne générale", f"{general_average:.2f} / 20" if general_average is not None else "—"],
        ["Rang", f"{class_rank} / {class_size}" if class_rank and class_size else "—"],
    ]
    summary_table = Table(summary_data, colWidths=[80 * mm, 80 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F6F5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
    ]))
    elements.append(summary_table)

    if appreciation:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("Appréciation générale", SECTION_STYLE))
        elements.append(Paragraph(appreciation, styles["Normal"]))

    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph("Signature du responsable pédagogique: ______________________", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def generate_report_cards_batch_pdf(report_cards: list[dict]) -> bytes:
    """
    Concatène plusieurs bulletins dans un seul PDF (un par élève, saut de
    page entre chaque) — pour l'impression en lot d'une classe entière.
    Chaque dict de `report_cards` a la même forme que les paramètres de
    `generate_report_card_pdf`.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    elements = []

    for i, rc in enumerate(report_cards):
        if i > 0:
            elements.append(PageBreak())

        elements.append(Paragraph(rc["school_name"], TITLE_STYLE))
        elements.append(Paragraph(
            f"Bulletin scolaire — {rc['academic_year_label']} — {rc['period_name']}", SUBTITLE_STYLE
        ))
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(
            f"<b>{rc['student_full_name']}</b> — Matricule {rc['student_matricule']} — Classe {rc['class_name']}",
            styles["Normal"],
        ))
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("Résultats par matière", SECTION_STYLE))

        table_data = [["Matière", "Moyenne / 20", "Coefficient"]]
        for subject in rc["subjects"]:
            avg = subject.get("average")
            table_data.append([
                subject.get("subject_name", ""),
                f"{avg:.2f}" if avg is not None else "—",
                str(subject.get("coefficient", "")),
            ])
        table = Table(table_data, repeatRows=1, colWidths=[80 * mm, 40 * mm, 40 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F5")]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6 * mm))

        general_average = rc.get("general_average")
        class_rank = rc.get("class_rank")
        class_size = rc.get("class_size")
        summary_data = [
            ["Moyenne générale", f"{general_average:.2f} / 20" if general_average is not None else "—"],
            ["Rang", f"{class_rank} / {class_size}" if class_rank and class_size else "—"],
        ]
        summary_table = Table(summary_data, colWidths=[80 * mm, 80 * mm])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F6F5")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        elements.append(summary_table)

    doc.build(elements)
    return buffer.getvalue()


def generate_receipt_pdf(
    school_name: str,
    receipt_number: str,
    student_name: str,
    student_matricule: str,
    amount: float,
    currency: str,
    method: str,
    paid_at: str,
    received_by_name: str,
    print_count: int,
    verification_url: str | None = None,
) -> bytes:
    """Reçu de paiement (§29 du cahier des charges: chaque paiement produit
    un reçu, imprimable / réimprimable et identifiable)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=25 * mm, bottomMargin=25 * mm,
                             leftMargin=30 * mm, rightMargin=30 * mm)

    method_labels = {
        "cash": "Espèces", "transfer": "Virement", "check": "Chèque",
        "mobile_money": "Mobile Money", "other": "Autre",
    }

    elements = [
        Paragraph(school_name, TITLE_STYLE),
        Paragraph("Reçu de paiement", SUBTITLE_STYLE),
        Spacer(1, 10 * mm),
    ]

    if print_count > 1:
        elements.append(Paragraph(f"<font color='#c0392b'><b>RÉIMPRESSION N°{print_count}</b></font>", styles["Normal"]))
        elements.append(Spacer(1, 4 * mm))

    data = [
        ["N° de reçu", receipt_number],
        ["Élève", f"{student_name} (matricule {student_matricule})"],
        ["Montant", f"{amount:,.0f} {currency}".replace(",", " ")],
        ["Moyen de paiement", method_labels.get(method, method)],
        ["Date", paid_at],
        ["Reçu par", received_by_name],
    ]
    table = Table(data, colWidths=[50 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F6F5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements += _verification_qr_elements(verification_url, "fr")
    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph("Signature: ______________________", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def generate_dashboard_stats_pdf(school_name: str, total_students: int, total_classes: int, by_level: list[dict]) -> bytes:
    buffer=io.BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,topMargin=18*mm,bottomMargin=18*mm)
    elements=[Paragraph(school_name,TITLE_STYLE),Paragraph("Rapport statistique de l’établissement",SUBTITLE_STYLE),Spacer(1,8*mm)]
    summary=Table([["Élèves actifs",str(total_students)],["Classes",str(total_classes)]],colWidths=[80*mm,80*mm])
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#F4F6F5")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),11)])); elements += [summary,Spacer(1,8*mm),Paragraph("Effectif par niveau",SECTION_STYLE)]
    data=[["Niveau","Effectif"]]+[[r["level_name"],str(r["effectif"])] for r in by_level]
    table=Table(data,colWidths=[100*mm,60*mm],repeatRows=1); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.4,colors.grey)])); elements.append(table); elements.append(Spacer(1,10*mm)); elements.append(Paragraph(f"Généré le {date.today().strftime('%d/%m/%Y')}",SUBTITLE_STYLE)); doc.build(elements); return buffer.getvalue()


def generate_competency_report_pdf(
    school_name: str,
    ministry_name: str,
    year_label: str,
    period_name: str,
    student,
    class_name: str,
    cycle: str,
    section: str,
    results: list[dict],
    scales: list[dict],
) -> bytes:
    """Carnet/bulletin compétence SIGMA pour maternelle et primaire.

    Le contenu est piloté par le référentiel enregistré en base: aucune
    compétence, matière ou cote n'est codée en dur dans le PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=12*mm, bottomMargin=14*mm,
                            leftMargin=12*mm, rightMargin=12*mm)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10)
    head = ParagraphStyle("Head", parent=styles["Heading2"], textColor=BRAND_GREEN, fontSize=11, leading=13)
    elements = [
        Paragraph("REPUBLIQUE DU CAMEROUN", TITLE_STYLE),
        Paragraph(ministry_name.upper(), SUBTITLE_STYLE),
        Spacer(1, 2*mm),
        Paragraph("CARNET SCOLAIRE — MATERNELLE & PRIMAIRE", TITLE_STYLE),
        Paragraph(f"Curriculum / référentiel : {section.upper()} — {cycle.upper()}", SUBTITLE_STYLE),
        Spacer(1, 4*mm),
    ]
    identity = [
        ["Élève", f"{student.last_name} {student.first_name}"],
        ["Matricule", student.matricule or "—"],
        ["Classe", class_name],
        ["Année scolaire", year_label],
        ["Période", period_name],
    ]
    t = Table(identity, colWidths=[38*mm, 140*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#F4F6F5")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTSIZE",(0,0),(-1,-1),9)]))
    elements += [t, Spacer(1, 5*mm), Paragraph("Légende de cotation", head)]
    legend = [[s.get("code",""), s.get("label", ""), s.get("description", "")] for s in scales]
    if legend:
        lt=Table([["Code","Appréciation","Description"]]+legend,colWidths=[25*mm,45*mm,108*mm],repeatRows=1)
        lt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)]))
        elements += [lt, Spacer(1,5*mm)]
    elements.append(Paragraph("Évaluations et observations", head))
    grouped = {}
    for r in results:
        grouped.setdefault(r.get("domain") or "Évaluation", []).append(r)
    for domain, rows in grouped.items():
        elements.append(Paragraph(domain, ParagraphStyle("Domain", parent=head, fontSize=10)))
        data=[["Compétence / critère","Mode","Résultat","Cote","Observation"]]
        for r in rows:
            if r.get("score") is not None and r.get("max_score"):
                result=f"{r['score']:.2f}/{r['max_score']:g}"
            else:
                result="—"
            data.append([r.get("competency") or r.get("criterion") or "—", r.get("mode") or "—", result, r.get("rating") or "—", r.get("observation") or ""])
        table=Table(data,colWidths=[54*mm,22*mm,25*mm,18*mm,59*mm],repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),7.5),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9F8")])]))
        elements += [table, Spacer(1,4*mm)]
    elements += [Spacer(1,4*mm), Paragraph("Bilan de l'enseignant", head), Paragraph("Points forts : __________________________________________________________________________________", small), Spacer(1,3*mm), Paragraph("Besoins d'accompagnement / remédiation : ______________________________________________________________", small), Spacer(1,3*mm), Paragraph("Appréciation générale : ______________________________________________________________________________", small), Spacer(1,10*mm)]
    sign=Table([["Visa enseignant\n\n________________________", "Visa directeur\n\n________________________", "Visa parents\n\n________________________"]],colWidths=[59*mm]*3)
    sign.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(0,0),(-1,-1),"CENTER"),("FONTSIZE",(0,0),(-1,-1),8)]))
    elements.append(sign)
    doc.build(elements)
    return buffer.getvalue()


def generate_bulletin_pdf(school_name: str, ministry_name: str, year_label: str, period_name: str, student, class_name: str, cycle: str, section: str, bulletin: dict, language: str = "fr", verification_url: str | None = None) -> bytes:
    """Bulletin opérationnel SIGMA v1.5, construit depuis le moteur de calcul.

    Ce rendu est un modèle SIGMA configurable et non une reproduction déclarée
    d'un formulaire officiel MINEDUB.
    """
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,topMargin=10*mm,bottomMargin=12*mm,leftMargin=10*mm,rightMargin=10*mm)
    title="SCHOOL REPORT / BULLETIN SCOLAIRE" if language=="en" else "BULLETIN SCOLAIRE"
    elements=[Paragraph("REPUBLIC OF CAMEROON" if language=="en" else "REPUBLIQUE DU CAMEROUN",TITLE_STYLE),Paragraph(ministry_name.upper(),SUBTITLE_STYLE),Spacer(1,2*mm),Paragraph(title,TITLE_STYLE),Paragraph(f"{section.upper()} — {cycle.upper()}",SUBTITLE_STYLE),Spacer(1,3*mm)]
    ident=[["Student / Élève",f"{student.last_name} {student.first_name}"],["Matricule",student.matricule or "—"],["Class / Classe",class_name],["Academic year / Année",year_label],["Period / Période",period_name]]
    t=Table(ident,colWidths=[42*mm,136*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#F4F6F5")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTSIZE",(0,0),(-1,-1),8.5)])); elements += [t,Spacer(1,4*mm)]
    avg=bulletin.get("average"); pct=bulletin.get("percent"); app=bulletin.get("appreciation") or {}
    summary_label="Overall average" if language=="en" else "Moyenne générale"
    app_label="General appreciation" if language=="en" else "Appréciation générale"
    summary=[[summary_label,f"{avg:.2f}/20" if avg is not None else "—"],["Percentage",f"{pct:.2f}%" if pct is not None else "—"]]
    if language == "en":
        summary += [["Letter grade", bulletin.get("grade") or "—"],["GPA",f"{bulletin.get('gpa'):.2f}/4.00" if bulletin.get("gpa") is not None else "—"]]
    summary += [[app_label,app.get("text") or "—"]]
    st=Table(summary,colWidths=[55*mm,123*mm]); st.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#F4F6F5")),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTSIZE",(0,0),(-1,-1),8.5)])); elements += [st,Spacer(1,4*mm)]
    if bulletin.get("subjects"):
        elements.append(Paragraph("Subjects / Matières",ParagraphStyle("BHead",parent=styles["Heading2"],textColor=BRAND_GREEN,fontSize=10,leading=12)))
        data=[["Subject / Matière","Average / Moyenne","%","Appreciation / Appréciation"]]
        for x in bulletin["subjects"]:
            a=x.get("average"); p=x.get("percent"); ap=x.get("appreciation") or {}
            data.append([x.get("subject_name") or "—",f"{a:.2f}/20" if a is not None else "—",f"{p:.1f}" if p is not None else "—",ap.get("text") or "—"])
        tb=Table(data,colWidths=[55*mm,30*mm,20*mm,73*mm],repeatRows=1); tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),7.5),("VALIGN",(0,0),(-1,-1),"TOP") ])); elements += [tb,Spacer(1,4*mm)]
    if bulletin.get("competencies"):
        elements.append(Paragraph("Competencies / Compétences",ParagraphStyle("CHead",parent=styles["Heading2"],textColor=BRAND_GREEN,fontSize=10,leading=12)))
        data=[["Competency / Compétence","Average / Moyenne","%","Appreciation / Appréciation"]]
        for x in bulletin["competencies"]:
            a=x.get("average"); p=x.get("percent"); ap=x.get("appreciation") or {}
            data.append([x.get("competency_name") or "—",f"{a:.2f}/20" if a is not None else "—",f"{p:.1f}" if p is not None else "—",ap.get("text") or "—"])
        tb=Table(data,colWidths=[65*mm,30*mm,20*mm,63*mm],repeatRows=1); tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),7.5),("VALIGN",(0,0),(-1,-1),"TOP") ])); elements += [tb,Spacer(1,5*mm)]
    elements += _verification_qr_elements(verification_url, language)
    elements += [Paragraph("Teacher's comments / Appréciation de l'enseignant : _________________________________________________",small),Spacer(1,8*mm),Paragraph("Decision / Décision : __________________________________________________________________________",small),Spacer(1,10*mm)]
    sign=Table([["Teacher / Enseignant\n\n__________________","Headteacher / Direction\n\n__________________","Parent / Tuteur\n\n__________________"]],colWidths=[59*mm]*3); sign.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)])); elements.append(sign)
    doc.build(elements); return buffer.getvalue()


def generate_enrollment_certificate_pdf(
    school_name: str,
    school_address: str | None,
    school_phone: str | None,
    academic_year_label: str,
    student_name: str,
    student_matricule: str,
    class_name: str,
    enrolled_at: str,
    guardian_name: str | None = None,
) -> bytes:
    """Attestation simple d'inscription, générée à partir des données SIGMA."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=22 * mm, bottomMargin=22 * mm,
                            leftMargin=25 * mm, rightMargin=25 * mm)
    elements = [
        Paragraph(school_name, TITLE_STYLE),
        Paragraph("Attestation d'inscription scolaire", ParagraphStyle(
            "CertTitle", parent=styles["Title"], textColor=BRAND_GREEN, fontSize=18, spaceAfter=12
        )),
    ]
    contact = " · ".join(x for x in [school_address, school_phone] if x)
    if contact:
        elements.append(Paragraph(contact, SUBTITLE_STYLE))
    elements += [
        Spacer(1, 16 * mm),
        Paragraph(
            f"Nous certifions que <b>{student_name}</b>, matricule <b>{student_matricule}</b>, "
            f"est régulièrement inscrit(e) en <b>{class_name}</b> au titre de l'année scolaire "
            f"<b>{academic_year_label}</b>.", styles["Normal"]
        ),
        Spacer(1, 8 * mm),
        Paragraph(f"Date d'inscription : <b>{enrolled_at}</b>", styles["Normal"]),
    ]
    if guardian_name:
        elements.append(Paragraph(f"Responsable principal déclaré : <b>{guardian_name}</b>", styles["Normal"]))
    elements += [
        Spacer(1, 25 * mm),
        Paragraph(f"Fait le {date.today().strftime('%d/%m/%Y')}", styles["Normal"]),
        Spacer(1, 18 * mm),
        Paragraph("Le responsable de l'établissement : ______________________________", styles["Normal"]),
        Spacer(1, 12 * mm),
        Paragraph("Cachet et signature", styles["Normal"]),
    ]
    doc.build(elements)
    return buffer.getvalue()


def generate_student_dossier_pdf(
    school_name: str,
    academic_year_label: str,
    student: dict,
    current_enrollment: dict | None,
    guardians: list[dict],
    enrollment_history: list[dict],
    finance_summary: dict | None = None,
) -> bytes:
    """Dossier administratif imprimable d'un élève."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    elements = [Paragraph(school_name, TITLE_STYLE),
                Paragraph(f"Dossier administratif élève — {academic_year_label}", SUBTITLE_STYLE),
                Spacer(1, 7 * mm)]
    identity = [
        ["Matricule", student.get("matricule", "—"), "Nom", student.get("last_name", "—")],
        ["Prénom", student.get("first_name", "—"), "Sexe", student.get("sex") or "—"],
        ["Naissance", student.get("birth_date") or "—", "Lieu", student.get("birth_place") or "—"],
        ["Nationalité", student.get("nationality") or "—", "Statut", student.get("status") or "—"],
        ["Adresse", student.get("address") or "—", "Classe", (current_enrollment or {}).get("class_name") or "—"],
    ]
    elements += [Paragraph("Identité", SECTION_STYLE), Table(identity, colWidths=[28*mm, 58*mm, 25*mm, 58*mm])]
    elements[-1].setStyle(TableStyle([("GRID",(0,0),(-1,-1),.35,colors.grey), ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"), ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"), ("VALIGN",(0,0),(-1,-1),"TOP")]))
    elements += [Spacer(1, 6*mm), Paragraph("Parents / tuteurs", SECTION_STYLE)]
    gd = [["Nom", "Lien", "Téléphone", "Retrait", "Principal"]]
    gd += [[f"{g.get('first_name','')} {g.get('last_name','')}", g.get('relationship_type') or "—", g.get('phone') or "—", "Oui" if g.get('can_pick_up_child') else "Non", "Oui" if g.get('is_primary_contact') else "—"] for g in guardians]
    if len(gd)==1: gd.append(["Aucun responsable", "—", "—", "—", "—"])
    t=Table(gd, repeatRows=1, colWidths=[43*mm,27*mm,38*mm,25*mm,25*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])); elements.append(t)
    elements += [Spacer(1, 6*mm), Paragraph("Historique scolaire", SECTION_STYLE)]
    hd=[["Année", "Classe", "Début", "Fin", "Type"]]
    hd += [[str(h.get('academic_year_id','—')),h.get('class_name') or '—',h.get('enrolled_at') or '—',h.get('left_at') or 'En cours',h.get('enrollment_type') or '—'] for h in enrollment_history]
    if len(hd)==1: hd.append(["—","Aucune inscription","—","—","—"])
    t=Table(hd, repeatRows=1, colWidths=[25*mm,50*mm,30*mm,30*mm,30*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),BRAND_GREEN),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])); elements.append(t)
    if finance_summary is not None:
        elements += [Spacer(1,6*mm), Paragraph("Situation financière synthétique", SECTION_STYLE)]
        elements.append(Table([["Facturé", f"{finance_summary.get('due',0):,.0f}"], ["Payé", f"{finance_summary.get('paid',0):,.0f}"], ["Solde", f"{finance_summary.get('balance',0):,.0f}"]], colWidths=[70*mm,70*mm], style=TableStyle([("GRID",(0,0),(-1,-1),.35,colors.grey),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold")])) )
    elements += [Spacer(1, 14*mm), Paragraph(f"Document généré par SIGMA le {date.today().strftime('%d/%m/%Y')}", SUBTITLE_STYLE)]
    doc.build(elements)
    return buffer.getvalue()
