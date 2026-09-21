"""
Passerelle SMS de SIGMA.

Le "boîtier" désigne le matériel physique de l'établissement (box GSM / téléphone
Android en SMS-gateway / modem série) qui envoie réellement les SMS. Comme le
modèle exact varie d'un établissement à l'autre, ce module expose une petite
interface `SmsDriver` avec deux implémentations prêtes à l'emploi :

  - "fake"  : n'envoie rien, journalise seulement (permet à SIGMA de tourner
              sans matériel branché, pendant les tests ou avant l'installation
              du boîtier).
  - "http"  : envoie une requête HTTP au boîtier, en supposant une API du
              type `POST {url} {"to": "...", "text": "...", "sender": "..."}`
              avec une clé API optionnelle en en-tête. C'est le protocole le
              plus courant pour les boîtiers SMS Android (ex: applications
              "SMS Gateway") et pour la plupart des box GSM commerciales.

Pour brancher un boîtier avec un protocole différent (AT commands sur port
série, API propriétaire...), il suffit d'ajouter une nouvelle classe qui
implémente `send(phone, body) -> (ok, provider_reference, error)` et de la
sélectionner dans `get_driver()`.
"""
from abc import ABC, abstractmethod
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsDriver(ABC):
    name = "unknown"
    is_simulation = False

    @abstractmethod
    def send(self, phone: str, body: str) -> tuple[bool, str | None, str | None]:
        """Retourne (succès, référence_fournisseur, message_erreur)."""
        raise NotImplementedError


class FakeDriver(SmsDriver):
    name = "fake"
    is_simulation = True
    """Ne fait aucun envoi réel. Utile en développement ou avant le
    branchement effectif du boîtier SMS de l'établissement."""

    def send(self, phone: str, body: str) -> tuple[bool, str | None, str | None]:
        print(f"[SMS-FAKE] -> {phone}: {body[:120]}")
        return True, "fake-driver", None


class HttpBoxDriver(SmsDriver):
    name = "http"
    is_simulation = False
    """Envoie via l'API HTTP locale du boîtier SMS (LAN de l'établissement)."""

    def send(self, phone: str, body: str) -> tuple[bool, str | None, str | None]:
        try:
            import httpx
        except ImportError:
            return False, None, "Le paquet 'httpx' est requis pour le mode SMS_GATEWAY_MODE=http"

        headers = {}
        if settings.SMS_GATEWAY_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SMS_GATEWAY_API_KEY}"

        try:
            response = httpx.post(
                settings.SMS_GATEWAY_URL,
                json={"to": phone, "text": body, "sender": settings.SMS_GATEWAY_SENDER_NAME},
                headers=headers,
                timeout=settings.SMS_GATEWAY_TIMEOUT_SECONDS,
            )
            if response.status_code >= 400:
                return False, None, f"Boîtier SMS: HTTP {response.status_code} — {response.text[:200]}"
            reference = None
            try:
                reference = str(response.json().get("id"))
            except Exception as exc:
                logger.warning("Réponse du boîtier SMS sans identifiant exploitable: %s", exc)
            return True, reference, None
        except Exception as exc:  # boîtier injoignable, timeout réseau local, etc.
            return False, None, f"Boîtier SMS injoignable: {exc}"


def get_driver() -> SmsDriver:
    mode = str(settings.SMS_GATEWAY_MODE or "fake").strip().lower()
    if mode == "http":
        return HttpBoxDriver()
    if mode == "fake":
        return FakeDriver()
    raise RuntimeError(f"SMS_GATEWAY_MODE invalide: {mode!r}. Valeurs supportées: fake, http")


def ensure_provider_allowed(driver: SmsDriver) -> None:
    """Empêche une installation de production de comptabiliser une simulation comme un vrai SMS."""
    if settings.ENV.lower() == "production" and driver.is_simulation and not settings.SMS_ALLOW_SIMULATION_IN_PRODUCTION:
        raise RuntimeError("Le fournisseur SMS est en mode SIMULATION: configurez un fournisseur réel avant l'envoi en production")
