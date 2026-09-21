"""
Configuration centrale de SIGMA Server.
Toutes les valeurs sont surchargeables via variables d'environnement (.env).
"""
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.paths import data_dir
from app.core.version import APP_VERSION, CHANNEL as RELEASE_CHANNEL

_DATA_DIR = data_dir()
_ENV_FILE = _DATA_DIR / ".env"


def scrub_initial_admin_password() -> bool:
    """Remove the one-time bootstrap password from persistent .env storage."""
    if not _ENV_FILE.exists():
        return False
    try:
        lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
        filtered = [line for line in lines if not line.startswith("SIGMA_INITIAL_ADMIN_PASSWORD=")]
        if len(filtered) == len(lines):
            return False
        _ENV_FILE.write_text("\n".join(filtered) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    APP_NAME: str = "SIGMA Server"
    APP_VERSION: str = APP_VERSION
    # V3_VERSION est désormais dérivée de la version du release manifest afin
    # d'éviter plusieurs sources de vérité. Le suffixe décrit le canal de
    # compatibilité, pas une seconde version numérique.
    V3_VERSION: str = f"{APP_VERSION}-hardening"
    RELEASE_VERSION: str = APP_VERSION
    RELEASE_CHANNEL: str = RELEASE_CHANNEL
    ENV: str = "development"

    # Base de données
    # SQLite par défaut : zéro configuration, fonctionne immédiatement pour
    # une première installation stable (école unique / petit réseau local).
    # Le chemin est ancré au dossier de données (à côté de l'exécutable en
    # mode .exe) pour que la base survive aux mises à jour et ne dépende pas
    # du dossier courant depuis lequel le programme a été lancé.
    # Pour PostgreSQL (recommandé au-delà d'un seul serveur / gros volumes),
    # remplacez par: postgresql+psycopg://user:pass@host:5432/sigma
    DATABASE_URL: str = f"sqlite:///{(_DATA_DIR / 'sigma.db').as_posix()}"

    # Sécurité / Authentification
    SECRET_KEY: str = ""
    # Secret d'amorçage écrit dans le .env par `run_server.py --setup`.
    # Il DOIT être déclaré ici : le fichier .env n'est pas chargé dans
    # os.environ, donc seed.py ne peut le retrouver que via les settings.
    # Sans cela, seed.py génère un second mot de passe, différent de celui
    # affiché à l'installateur, et plus personne ne peut se connecter.
    # Il est effacé du .env par scrub_initial_admin_password() dès que le
    # compte administrateur existe.
    SIGMA_INITIAL_ADMIN_PASSWORD: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8h
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours
    # None = comportement automatique historique (Secure en production).
    # Une installation Windows locale en HTTP/loopback peut l'expliciter à false.
    AUTH_COOKIE_SECURE: bool | None = None
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_RATE_LIMIT: int = 5
    PASSWORD_RESET_RATE_WINDOW_SECONDS: int = 900
    RATE_LIMIT_REDIS_URL: str = ""
    RATE_LIMIT_REDIS_PREFIX: str = "sigma:ratelimit:"
    RATE_LIMIT_FAIL_CLOSED: bool = False
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    # SMTP — nécessaire pour l'auto-récupération par email en production.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True

    # Sécurité des comptes
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    LOGIN_RATE_LIMIT: int = 12
    LOGIN_RATE_WINDOW_SECONDS: int = 60
    BADGE_VERIFY_RATE_LIMIT: int = 120
    BADGE_VERIFY_RATE_WINDOW_SECONDS: int = 60
    WEBHOOK_MAX_BODY_BYTES: int = 256 * 1024

    # Réseau / serveur
    # 0.0.0.0 permet aux postes clients du LAN de joindre le serveur SIGMA.
    BIND_HOST: str = "0.0.0.0"
    PORT: int = 8000
    OPEN_BROWSER: bool = True

    # CORS
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # Passerelle SMS ("le boîtier")
    # mode "fake"  -> aucun envoi réel, tout est journalisé (par défaut, pour marcher out-of-the-box)
    # mode "http"  -> POST HTTP vers l'API locale du boîtier SMS (GSM box / gateway Android)
    SMS_GATEWAY_MODE: str = "fake"
    SMS_GATEWAY_URL: str = "http://192.168.1.50:8080/send"  # adresse locale typique du boîtier sur le LAN
    SMS_GATEWAY_API_KEY: str = ""
    SMS_GATEWAY_SENDER_NAME: str = "SIGMA"
    SMS_GATEWAY_TIMEOUT_SECONDS: int = 10
    # Simulation SMS is allowed for development/pilot only. A production
    # installation must have a real provider unless this is explicitly enabled
    # for a controlled test environment.
    SMS_ALLOW_SIMULATION_IN_PRODUCTION: bool = False

    # Web Push / PWA
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@example.com"

    # Cartes scolaires / cartes d'accès
    CARD_QR_ENABLED: bool = True
    CARD_DEFAULT_VALIDITY_YEARS: int = 1

    # Fichiers média (photos élèves, bulletins PDF générés, imports Excel)
    # Ancré au dossier de données pour la même raison que DATABASE_URL ci-dessus.
    MEDIA_ROOT: str = str(_DATA_DIR / "media")
    MAX_PHOTO_SIZE_MB: int = 5
    MAX_IMPORT_UPLOAD_BYTES: int = 20 * 1024 * 1024
    MAX_SCHOOL_ASSET_BYTES: int = 5 * 1024 * 1024
    ALLOWED_PHOTO_EXTENSIONS: Annotated[list[str], NoDecode] = [".jpg", ".jpeg", ".png"]

    # pydantic-settings exige du JSON strict pour les champs list[]/dict[]
    # lus depuis .env (ex: CORS_ORIGINS=["http://a","http://b"]). Un .env
    # rempli à la main avec une valeur simple ("http://a,http://b" ou une
    # ligne vide) fait planter le serveur AVANT même le démarrage du
    # bootloader PyInstaller, avec une JSONDecodeError peu lisible pour un
    # non-développeur. On accepte donc en plus : chaîne vide -> valeur par
    # défaut, et liste séparée par virgules -> liste. Le JSON reste
    # supporté pour compatibilité avec les .env déjà corrects.
    @staticmethod
    def _parse_env_list(v, default):
        if v is None:
            return default
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if stripped == "":
                return default
            if stripped.startswith("["):
                import json

                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _validate_cors_origins(cls, v):
        return cls._parse_env_list(v, [])

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _validate_cors_policy(cls, v):
        origins = [str(x).strip() for x in (v or []) if str(x).strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS ne peut pas contenir '*' lorsque les credentials sont autorisés")
        return origins

    @field_validator("ALLOWED_PHOTO_EXTENSIONS", mode="before")
    @classmethod
    def _validate_allowed_photo_extensions(cls, v):
        return cls._parse_env_list(v, [".jpg", ".jpeg", ".png"])

    # Exploitation / production
    REQUEST_ID_HEADER: str = "X-Request-ID"
    MAX_BACKUPS_TO_KEEP: int = 30
    BACKUP_MAX_ARCHIVE_BYTES: int = 2 * 1024 * 1024 * 1024
    BACKUP_MAX_FILE_BYTES: int = 1024 * 1024 * 1024
    BACKUP_MAX_TOTAL_BYTES: int = 2 * 1024 * 1024 * 1024
    RESTORE_MAX_UPLOAD_BYTES: int = 2 * 1024 * 1024 * 1024
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # Performance / capacité
    GZIP_ENABLED: bool = True
    GZIP_MINIMUM_SIZE: int = 1024
    OBSERVABILITY_SAMPLE_LIMIT: int = 2000
    SLOW_REQUEST_THRESHOLD_MS: int = 1000
    # SLA / exploitation: these values are monitoring thresholds, not contractual guarantees.
    SLA_TARGET_PERCENT: float = 99.5
    SLA_MAX_5XX_PERCENT: float = 2.0
    SLA_MAX_P95_MS: int = 1000
    INCIDENT_AUTOMATION_COOLDOWN_SECONDS: int = 300
    INCIDENT_AUTOMATION_MAX_ACTIONS: int = 3

    # Mise à jour automatique — désactivée par défaut.
    UPDATE_ENABLED: bool = False
    UPDATE_MANIFEST_URL: str = ""
    UPDATE_CHANNEL: str = "commercial"
    UPDATE_POLL_INTERVAL_SECONDS: int = 3600
    UPDATE_MAX_ARTIFACT_BYTES: int = 2 * 1024 * 1024 * 1024

    # Paiements entrants — webhook générique signé. Désactivé tant qu'un secret
    # n'est pas explicitement configuré. Le secret n'est jamais exposé par l'API.
    PAYMENT_WEBHOOK_SECRET: str = ""
    PAYMENT_WEBHOOK_MAX_AGE_SECONDS: int = 300
    PAYMENT_WEBHOOK_PROVIDER: str = "generic"

    # Intelligence artificielle — désactivée par défaut tant qu'un fournisseur
    # et une politique de données n'ont pas été explicitement configurés.
    AI_PROVIDER: str = "disabled"  # disabled | local | openai_compatible
    AI_MODEL: str = ""
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_TIMEOUT_SECONDS: int = 30
    AI_ALLOW_PERSONAL_DATA_TO_PROVIDER: bool = False
    # Le contenu des documents institutionnels peut lui-même contenir des
    # données personnelles. Sa transmission à un fournisseur externe est donc
    # soumise à un consentement technique distinct.
    AI_ALLOW_KNOWLEDGE_TO_PROVIDER: bool = False
    AI_MAX_OUTPUT_TOKENS: int = 1200
    # Réponses documentaires fiables : lorsque activé, SIGMA AI refuse une
    # réponse institutionnelle si aucune source publiée pertinente n'est retrouvée.
    AI_GROUNDED_ONLY: bool = True
    AI_KNOWLEDGE_MIN_SCORE: float = 0.12
    # Les exécutions IA restent désactivées par défaut. Une action doit
    # d’abord être approuvée par un humain puis franchir ce garde-fou système.
    AI_ACTION_EXECUTION_ENABLED: bool = False
    AI_ACTION_MAX_RECIPIENTS: int = 100


settings = Settings()
if settings.ENV.lower() == "production" and not settings.RATE_LIMIT_REDIS_URL:
    settings.RATE_LIMIT_FAIL_CLOSED = False  # conserver la disponibilité; déployer Redis est néanmoins recommandé

# V4.39 incident automation safety controls
# Number of automatic incident actions permitted inside the cooldown window.
