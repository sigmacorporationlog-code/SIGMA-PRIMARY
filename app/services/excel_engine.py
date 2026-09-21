"""
Moteur Excel de SIGMA (openpyxl). Deux usages :

  1. Export : n'importe quelle liste de dicts -> classeur .xlsx propre
     (en-têtes en gras, couleur de marque, colonnes auto-ajustées).
  2. Import : lecture d'un classeur élèves selon un gabarit de colonnes fixe,
     avec validation ligne par ligne et rapport d'erreurs détaillé (aucune
     ligne ne doit faire échouer tout le fichier).
"""
import io
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BRAND_GREEN = "11633A"
BRAND_ORANGE = "FF8A00"

STUDENT_IMPORT_COLUMNS = [
    "Matricule", "Prénom", "Nom", "Date de naissance (AAAA-MM-JJ)",
    "Lieu de naissance", "Sexe (M/F)", "Nationalité", "Adresse",
]


def export_rows_to_xlsx(headers: list[str], rows: list[list], sheet_title: str = "Export") -> bytes:
    """Génère un classeur .xlsx à partir d'en-têtes + lignes brutes."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # limite Excel

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color=BRAND_GREEN, end_color=BRAND_GREEN, fill_type="solid")

    for col_index, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_index, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_index, row in enumerate(rows, start=2):
        for col_index, value in enumerate(row, start=1):
            ws.cell(row=row_index, column=col_index, value=value)

    # Ajustement approximatif de la largeur des colonnes
    for col_index, header in enumerate(headers, start=1):
        max_length = max([len(str(header))] + [len(str(r[col_index - 1])) for r in rows if r[col_index - 1] is not None] or [10])
        ws.column_dimensions[get_column_letter(col_index)].width = min(max_length + 4, 40)

    ws.freeze_panes = "A2"

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_students_xlsx(students: list[dict]) -> bytes:
    headers = ["Matricule", "Prénom", "Nom", "Date de naissance", "Sexe", "Nationalité", "Statut", "Classe"]
    rows = [
        [
            s.get("matricule"), s.get("first_name"), s.get("last_name"),
            s.get("birth_date").isoformat() if s.get("birth_date") else None,
            s.get("sex"), s.get("nationality"), s.get("status"), s.get("class_name"),
        ]
        for s in students
    ]
    return export_rows_to_xlsx(headers, rows, sheet_title="Élèves")


def build_student_import_template() -> bytes:
    """Classeur vierge avec les en-têtes attendues, à distribuer aux
    secrétariats pour une saisie en masse (§21 du cahier des charges:
    'import Excel')."""
    return export_rows_to_xlsx(STUDENT_IMPORT_COLUMNS, rows=[], sheet_title="Modèle import élèves")


class StudentImportRowError(Exception):
    def __init__(self, row_number: int, message: str):
        self.row_number = row_number
        self.message = message
        super().__init__(f"Ligne {row_number}: {message}")


def parse_students_import(file_bytes: bytes) -> list[dict]:
    """
    Lit un classeur élèves et retourne une liste de dicts prêts à être
    insérés. Lève StudentImportRowError sur la première ligne invalide
    rencontrée (le routeur API décide s'il arrête tout ou ignore la ligne).
    """
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    try:
        header_row = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    except StopIteration:
        raise StudentImportRowError(1, "Le fichier est vide (aucune ligne d'en-tête trouvée)")
    normalized_header = [str(h).strip() if h else "" for h in header_row]

    def col_index(name: str) -> int | None:
        try:
            return normalized_header.index(name)
        except ValueError:
            return None

    idx = {
        "matricule": col_index("Matricule"),
        "first_name": col_index("Prénom"),
        "last_name": col_index("Nom"),
        "birth_date": col_index("Date de naissance (AAAA-MM-JJ)"),
        "birth_place": col_index("Lieu de naissance"),
        "sex": col_index("Sexe (M/F)"),
        "nationality": col_index("Nationalité"),
        "address": col_index("Adresse"),
    }

    if idx["matricule"] is None or idx["first_name"] is None or idx["last_name"] is None:
        raise StudentImportRowError(1, "Colonnes obligatoires manquantes: Matricule, Prénom, Nom")

    results = []
    for row_number, row in enumerate(ws.iter_rows(min_row=2), start=2):
        values = [cell.value for cell in row]
        if all(v in (None, "") for v in values):
            continue  # ligne vide, ignorée silencieusement

        def get(field):
            i = idx[field]
            return values[i] if i is not None and i < len(values) else None

        matricule = get("matricule")
        first_name = get("first_name")
        last_name = get("last_name")
        if not matricule or not first_name or not last_name:
            raise StudentImportRowError(row_number, "Matricule, Prénom et Nom sont obligatoires")

        birth_date_raw = get("birth_date")
        birth_date = None
        if birth_date_raw:
            if isinstance(birth_date_raw, (date, datetime)):
                birth_date = birth_date_raw.date() if isinstance(birth_date_raw, datetime) else birth_date_raw
            else:
                try:
                    birth_date = date.fromisoformat(str(birth_date_raw).strip())
                except ValueError:
                    raise StudentImportRowError(row_number, f"Date de naissance invalide: {birth_date_raw!r} (attendu AAAA-MM-JJ)")

        sex = get("sex")
        if sex:
            sex = str(sex).strip().upper()[:1]
            if sex not in ("M", "F"):
                raise StudentImportRowError(row_number, f"Sexe invalide: {sex!r} (attendu M ou F)")

        results.append({
            "matricule": str(matricule).strip(),
            "first_name": str(first_name).strip(),
            "last_name": str(last_name).strip(),
            "birth_date": birth_date,
            "birth_place": str(get("birth_place")).strip() if get("birth_place") else None,
            "sex": sex,
            "nationality": str(get("nationality")).strip() if get("nationality") else None,
            "address": str(get("address")).strip() if get("address") else None,
            "_row_number": row_number,
        })

    return results
