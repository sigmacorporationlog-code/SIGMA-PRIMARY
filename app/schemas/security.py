from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from app.services.phone import normalize_international_phone


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    identifier: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class AdminPasswordReset(BaseModel):
    new_password: str
    force_change: bool = True


class UserCreate(BaseModel):
    school_id: int
    username: str
    email: EmailStr | None = None
    phone: str | None = None
    password: str
    first_name: str
    last_name: str

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v):
        return normalize_international_phone(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    username: str
    # Volontairement `str` et non `EmailStr` ici : ceci est un schéma de
    # SORTIE (réponse API), pas de saisie. `EmailStr` re-valide la valeur
    # à CHAQUE lecture, y compris pour des comptes déjà existants en base.
    # Si un email stocké devient invalide selon les règles de la version
    # d'email-validator installée (ex: domaines réservés comme .local/
    # .test/.invalid, ou un futur durcissement de la bibliothèque), CET
    # ENDPOINT PLANTE EN 500 POUR TOUJOURS, y compris /api/auth/me appelé
    # à chaque navigation — ce qui produit exactement le symptôme "je suis
    # bien connecté mais SIGMA me renvoie sans arrêt à l'écran de
    # connexion". La validation stricte reste sur UserCreate (saisie),
    # où elle a sa place : empêcher qu'une adresse invalide soit ENREGISTRÉE.
    # Elle ne doit jamais empêcher de LIRE un compte déjà enregistré.
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    is_active: bool
    is_superadmin: bool
    last_login_at: datetime | None
    must_change_password: bool


class PostCreate(BaseModel):
    school_id: int
    name: str
    description: str | None = None


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    name: str
    description: str | None


class PostPermissionAssign(BaseModel):
    permission_code: str
    scope: dict = {}


class PostPermissionBulkAssign(BaseModel):
    """Attribution en une fois de plusieurs permissions à un poste — celles
    cochées dans l'écran de création/édition d'un poste."""
    permission_codes: list[str]
    scope: dict = {}


class UserPostAssign(BaseModel):
    user_id: int
    post_id: int


class DelegationCreate(BaseModel):
    school_id: int
    granted_by_id: int
    granted_to_id: int
    permission_code: str
    scope: dict = {}
    start_date: str  # ISO date
    end_date: str
    reason: str | None = None
