"""
Moteur de cartes SIGMA.

Génère une carte (élève ou personnel) en HTML autonome, prêt à être imprimé
(ou exporté en PDF via la fonction "Imprimer" du navigateur). Approche
volontairement sans dépendance lourde de rendu PDF côté serveur, pour rester
simple à déployer sur un petit serveur d'établissement.

Si le paquet optionnel "qrcode" est installé, un vrai QR code (encodant le
`access_code` de la carte) est intégré en base64. Sinon, le code est affiché
en texte / code-barres textuel simplifié, sans bloquer la génération.
"""
import base64
import io
import secrets
from datetime import date

try:
    import qrcode

    QRCODE_AVAILABLE = True
except ImportError:  # pragma: no cover - dépendance optionnelle
    QRCODE_AVAILABLE = False


def generate_access_code() -> str:
    """Code aléatoire encodé dans le QR / la puce de la carte."""
    return secrets.token_hex(16)


def generate_card_number(sequence: int, prefix: str = "CARD") -> str:
    year = date.today().year
    return f"{prefix}-{year}-{sequence:06d}"


def _qr_base64(payload: str) -> str | None:
    if not QRCODE_AVAILABLE:
        return None
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def render_card_html(
    school_name: str,
    holder_name: str,
    subtitle: str,
    fields: dict[str, str],
    card_number: str,
    access_code: str,
    expires_at: str | None,
    layout: dict,
    photo_data_uri: str | None = None,
    logo_data_uri: str | None = None,
    stamp_data_uri: str | None = None,
    ministry_name: str | None = None,
    school_phones: str | None = None,
) -> str:
    """Rend une carte unique en HTML (une div de la taille d'une carte CR80)."""
    primary = layout.get("primary_color", "#11633A")
    accent = layout.get("accent_color", "#FF8A00")
    show_qr = layout.get("show_qr", True)

    qr_b64 = _qr_base64(f"SIGMA-BADGE:{access_code}") if show_qr else None
    qr_html = (
        f'<img class="qr" src="data:image/png;base64,{qr_b64}" alt="QR" />'
        if qr_b64
        else f'<div class="qr qr-fallback">{access_code[:16]}</div>'
    )

    photo_html = (
        f'<img class="photo" src="{photo_data_uri}" alt="photo" />'
        if photo_data_uri
        else '<div class="photo photo-placeholder"></div>'
    )

    fields_html = "".join(
        f'<div class="field"><span class="label">{label}</span><span class="value">{value}</span></div>'
        for label, value in fields.items()
    )

    return f"""
    <div class="sigma-card" style="--primary: {primary}; --accent: {accent};">
      <div class="card-header">
        {f'<img class="school-logo" src="{logo_data_uri}" />' if logo_data_uri else ''}
        <div><span class="ministry">{ministry_name or ''}</span><span class="school-name">{school_name}</span>
        <span class="subtitle">{subtitle}</span>{f'<span class="phones">{school_phones}</span>' if school_phones else ''}</div>
      </div>
      <div class="card-body">
        {photo_html}
        <div class="card-fields">
          <div class="holder-name">{holder_name}</div>
          {fields_html}
        </div>
        {qr_html}
      </div>
      <div class="card-footer">
        {f'<img class="school-stamp" src="{stamp_data_uri}" />' if stamp_data_uri else ''}
        <span class="card-number">{card_number}</span>
        <span class="expiry">{"Valide jusqu'au " + expires_at if expires_at else "Sans expiration"}</span>
      </div>
    </div>
    """


CARD_PAGE_STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Exo+2:wght@600;700&family=Montserrat:wght@400;500&display=swap" rel="stylesheet">
<style>
  body { font-family: 'Montserrat', Arial, sans-serif; background: #eee; padding: 24px; }
  .sigma-card {
    width: 340px; height: 210px; border-radius: 14px; overflow: hidden;
    background: white; box-shadow: 0 2px 10px rgba(0,0,0,.25);
    display: inline-flex; flex-direction: column; margin: 10px; page-break-inside: avoid;
  }
  .card-header {
    background: linear-gradient(120deg, var(--primary), var(--primary) 70%, var(--accent) 100%);
    color: white; padding: 8px 12px; display: flex; flex-direction: column;
  }
  .school-logo { width:30px; height:30px; object-fit:contain; margin-right:8px; background:white; border-radius:4px; }
  .ministry { display:block; font-size:7px; opacity:.8; }
  .phones { display:block; font-size:7px; opacity:.8; }
  .school-name { font-family: 'Exo 2', Arial, sans-serif; font-weight: 700; font-size: 13px; }
  .subtitle { font-size: 10px; opacity: .85; }
  .card-body { flex: 1; display: flex; align-items: center; padding: 10px; gap: 10px; }
  .photo { width: 64px; height: 78px; object-fit: cover; border-radius: 6px; border: 1px solid #ddd; }
  .photo-placeholder { background: #ddd; }
  .card-fields { flex: 1; }
  .holder-name { font-family: 'Exo 2', Arial, sans-serif; font-weight: 600; font-size: 14px; margin-bottom: 4px; color: var(--primary); }
  .field { font-size: 10px; display: flex; gap: 4px; }
  .field .label { color: #888; min-width: 60px; }
  .qr { width: 56px; height: 56px; }
  .qr-fallback { font-size: 8px; word-break: break-all; width: 56px; }
  .school-stamp { width:32px; height:24px; object-fit:contain; }
  .card-footer {
    display: flex; align-items:center; justify-content: space-between; font-size: 9px;
    padding: 4px 12px; background: #f4f4f4; color: #666;
  }
</style>
"""


def render_card_page(cards_html: list[str]) -> str:
    body = "\n".join(cards_html)
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{CARD_PAGE_STYLE}</head><body>{body}</body></html>"
