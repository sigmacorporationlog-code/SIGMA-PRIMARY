"""Regression : /api/auth/me plantait en 500 a CHAQUE appel (pas seulement
au premier), a cause d'une double faute :

1. seed.py creait l'admin initial avec un email fictif sur un domaine
   reserve (admin@sigma.local, RFC 6762 mDNS). email-validator refuse ce
   domaine meme en simple verification de syntaxe (pas de reseau requis).
2. UserOut (schema de REPONSE, pas de saisie) typait `email: EmailStr`,
   ce qui revalide n'importe quel email deja stocke a CHAQUE lecture.

Consequence observee en conditions reelles : apres une connexion reussie
(login 200), CHAQUE appel a /api/auth/me repond 500, en boucle, meme apres
un refresh de token reussi. Cote interface, sigma.js interprete cet echec
comme une session invalide et republie l'ecran de connexion a chaque
changement de page -- alors que l'utilisateur est bel et bien connecte.

Le correctif porte sur les deux fautes : seed.py n'invente plus d'email
(email=None, le champ est nullable), et UserOut utilise `str` au lieu de
`EmailStr` puisqu'il s'agit d'un schema de sortie -- la validation stricte
reste sur UserCreate (saisie), la ou elle a sa place.
"""
import importlib
import sys

import pytest


def test_seed_does_not_invent_a_reserved_domain_email_for_admin():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "seed.py").read_text(
        encoding="utf-8"
    )
    assert '"admin@sigma.local"' not in source
    assert "email=None" in source


def test_user_out_schema_does_not_revalidate_email_on_read():
    # UserOut est un schema de SORTIE : une valeur deja stockee ne doit
    # jamais pouvoir faire planter sa propre lecture. La validation
    # stricte (EmailStr) reste sur UserCreate, le schema de SAISIE.
    from app.schemas.security import UserOut, UserCreate

    assert UserOut.model_fields["email"].annotation in (str | None, "str | None")
    # UserCreate doit rester strict : on ne veut PAS accepter un email
    # invalide au moment ou l'utilisateur (ou un admin) le saisit.
    create_annotation = UserCreate.model_fields["email"].annotation
    assert "EmailStr" in str(create_annotation)


def test_user_out_serializes_reserved_domain_email_without_crashing():
    # Meme si un email invalide existe deja en base (legacy, import,
    # ancienne regle d'email-validator...), le lire ne doit jamais lever.
    from app.schemas.security import UserOut

    class _FakeUser:
        id = 1
        school_id = 1
        username = "admin"
        email = "admin@sigma.local"  # domaine reserve, refuse par EmailStr
        phone = None
        first_name = "Administrateur"
        last_name = "Systeme"
        is_active = True
        is_superadmin = True
        last_login_at = None
        must_change_password = True

    out = UserOut.model_validate(_FakeUser())
    assert out.email == "admin@sigma.local"
