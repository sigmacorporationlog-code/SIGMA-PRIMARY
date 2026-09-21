"""
Gestion des fichiers média de SIGMA: photos des élèves (et, demain, du
personnel). Les fichiers sont stockés sur disque sous MEDIA_ROOT, jamais en
base de données (seul le chemin relatif est stocké sur l'entité).

Toute photo importée est validée et normalisée (via Pillow, déjà une
dépendance de SIGMA pour les QR codes) : format JPEG, taille plafonnée, et
orientation EXIF corrigée — utile car les photos prises au téléphone
(le cas le plus courant en établissement scolaire) ont souvent une
orientation EXIF qui les affiche à l'envers si on ne la corrige pas.
"""
import io
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_DIMENSION = (600, 800)
MAX_PHOTO_PIXELS = 12_000_000


def media_root() -> Path:
    root = Path(settings.MEDIA_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_upload(file: UploadFile, raw: bytes) -> None:
    if len(raw) > settings.MAX_PHOTO_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Photo trop volumineuse (max {settings.MAX_PHOTO_SIZE_MB} Mo)")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in settings.ALLOWED_PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporté ({extension or 'inconnu'}). Formats acceptés: {', '.join(settings.ALLOWED_PHOTO_EXTENSIONS)}",
        )


def save_student_photo(student_id: int, file: UploadFile, raw: bytes) -> str:
    """
    Valide, normalise (recadrage/redimensionnement, orientation EXIF) et
    enregistre la photo d'un élève. Retourne le chemin relatif à stocker
    dans Student.photo_path.
    """
    _validate_upload(file, raw)

    students_dir = media_root() / "students"
    students_dir.mkdir(parents=True, exist_ok=True)
    destination = students_dir / f"{student_id}.jpg"

    try:
        from PIL import Image, ImageOps

        Image.MAX_IMAGE_PIXELS = MAX_PHOTO_PIXELS
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > MAX_PHOTO_PIXELS:
            raise HTTPException(status_code=413, detail="Image trop grande en nombre de pixels")
        image = ImageOps.exif_transpose(image)  # corrige l'orientation EXIF (photos prises au téléphone)
        image = image.convert("RGB")
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((600, 600))
        image.save(destination, format="JPEG", quality=88, optimize=True)
    except ImportError as exc:
        # En production, une photo ne doit jamais contourner la validation parce
        # qu'un moteur de traitement d'image est absent.
        raise HTTPException(status_code=503, detail="Le moteur de traitement d'images est indisponible") from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Fichier image invalide: {exc}")

    return f"students/{student_id}.jpg"


def resolve_media_path(relative_path: str) -> Path:
    """Resolve a stored media path without allowing filesystem traversal."""
    root = media_root().resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Chemin média invalide") from exc
    return candidate


def delete_student_photo(student_id: int) -> None:
    path = media_root() / "students" / f"{student_id}.jpg"
    if path.exists():
        path.unlink()


def save_school_asset(school_id: int, asset_type: str, file: UploadFile, raw: bytes) -> str:
    _validate_upload(file, raw)
    from PIL import Image, ImageOps
    folder = media_root() / "schools" / str(school_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{asset_type}.jpg"
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        image.thumbnail((1600, 1600)); image.save(dest, "JPEG", quality=90)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Image invalide: {exc}")
    return f"schools/{school_id}/{asset_type}.jpg"
