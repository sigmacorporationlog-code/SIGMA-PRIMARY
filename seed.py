"""
Initialise la base SIGMA:
  1. Crée toutes les tables (si Alembic n'a pas encore été utilisé).
  2. Charge le catalogue de permissions atomiques.
  3. Crée un établissement de démonstration + un administrateur superadmin.

Usage:
    python seed.py
"""
from datetime import date
import os
import sys
import secrets
import string

# Sécurité défensive : certaines consoles Windows (code page cp1252, ou
# redirection de sortie standard non UTF-8 selon l'environnement d'exécution)
# ne savent pas encoder certains caractères. Un simple print() avec un tel
# caractère levait alors une UnicodeEncodeError qui interrompait toute
# l'initialisation (base de données créée, mais message final jamais
# affiché) — reproduit lors du build Windows du 19/09/2026. On tolère
# désormais ces caractères en les remplaçant plutôt que de planter.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError, OSError):
        pass

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, ensure_schema_compatibility
from app.core.security import hash_password
import app.models  # noqa: F401  (charge tous les modèles dans Base.metadata)
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.security import User, Permission, Post, PostPermission, UserPost
from app.models.documents import CardTemplate
from app.models.evaluation import EvaluationFramework, EvaluationDomain, EvaluationCompetency, EvaluationCriterion, RatingScale, AppreciationRule

from app.services.permission_catalog import PERMISSIONS as PERMISSION_SPECS

PERMISSION_CATALOG = [(p.code, p.module, p.label) for p in PERMISSION_SPECS]



def seed_evaluation_frameworks(db, school, year):
    """Charge/complète les référentiels Maternelle & Primaire inspirés du cadre MINEDUB 2018.

    Le contenu reste éditable dans SIGMA. Les critères ci-dessous constituent un
    catalogue de départ détaillé; une école peut les adapter à son niveau, sa classe
    et ses pratiques d'évaluation sans modifier le code.
    """
    definitions = {
        ("fr", "nursery"): {
            "name": "Référentiel MINEDUB 2018 — Maternelle Francophone",
            "domains": [
                ("D1", "Langue et communication", 35, [
                    "S'exprimer oralement pour communiquer un message simple",
                    "Écouter et comprendre une consigne, une histoire ou un échange",
                    "Participer à des comptines, chants, récitations et jeux de langage",
                    "Développer le graphisme et les premiers gestes liés à l'écrit",
                    "Reconnaître et utiliser des mots, signes, images et symboles usuels",
                    "Participer aux activités d'anglais et/ou de langue nationale prévues par l'école",
                ]),
                ("D2", "Éveil scientifique et technologique", 25, [
                    "Observer, comparer et classer des objets, formes, couleurs et grandeurs",
                    "Utiliser des notions mathématiques élémentaires dans des situations concrètes",
                    "Se repérer dans l'espace et dans le temps",
                    "Observer le vivant, l'environnement et quelques phénomènes simples",
                    "Utiliser des outils et supports technologiques avec accompagnement",
                ]),
                ("D3", "Vie courante", 25, [
                    "Respecter les règles de vie, d'hygiène et de sécurité",
                    "Développer l'autonomie dans les gestes de la vie quotidienne",
                    "Adopter des comportements favorables à la santé et à la nutrition",
                    "Respecter les autres, le matériel et l'environnement",
                    "Participer à la vie du groupe et coopérer avec les autres",
                ]),
                ("D4", "Création artistique et activités manuelles", 10, [
                    "Dessiner, colorier et produire des réalisations graphiques",
                    "Explorer les couleurs, formes et matières",
                    "Réaliser des activités manuelles adaptées à l'âge",
                    "Chanter, danser, jouer et s'exprimer artistiquement",
                ]),
                ("D5", "Motricité générale", 5, [
                    "Coordonner ses mouvements et se déplacer avec aisance",
                    "Participer aux jeux collectifs et activités physiques",
                    "Respecter des consignes simples dans les activités motrices",
                ]),
            ],
            "scales": [
                ("A", "Acquis", 0, 100, "Compétence acquise"),
                ("ECA", "En cours d'acquisition", 0, 100, "Compétence en cours d'acquisition"),
                ("NA", "Non acquis", 0, 100, "Compétence non acquise"),
            ],
        },
        ("en", "nursery"): {
            "name": "2018 MINEDUB Framework — Nursery English",
            "domains": [
                ("D1", "Literacy and Communication", 35, [
                    "Express ideas and needs orally in simple situations",
                    "Listen and respond to simple instructions and stories",
                    "Participate in songs, rhymes, poems and language games",
                    "Develop pre-writing and early graphic skills",
                    "Recognise and use familiar words, pictures and symbols",
                    "Participate in English and/or national language activities provided by the school",
                ]),
                ("D2", "Science and Technology", 25, [
                    "Observe, compare and classify objects, shapes, colours and sizes",
                    "Use basic mathematical ideas in concrete situations",
                    "Identify simple spatial and temporal relationships",
                    "Observe living things, the environment and simple phenomena",
                    "Use simple technological tools and learning supports with guidance",
                ]),
                ("D3", "Practical Life", 25, [
                    "Follow hygiene, safety and classroom routines",
                    "Demonstrate increasing independence in daily activities",
                    "Adopt healthy and safe habits",
                    "Respect people, materials and the environment",
                    "Participate and cooperate in group activities",
                ]),
                ("D4", "Arts and Crafts", 10, [
                    "Draw, colour and produce graphic work",
                    "Explore colours, shapes, textures and materials",
                    "Complete age-appropriate craft activities",
                    "Sing, dance, play and express ideas creatively",
                ]),
                ("D5", "Motor Skills", 5, [
                    "Coordinate movements and move with confidence",
                    "Participate in physical and group games",
                    "Follow simple instructions during motor activities",
                ]),
            ],
            "scales": [
                ("1", "Excellent", 80, 100, "Performs independently and consistently"),
                ("2", "Satisfactory", 60, 79.99, "Performs with limited support"),
                ("3", "Average", 40, 59.99, "Performs with regular support"),
                ("4", "Poor", 20, 39.99, "Needs substantial support"),
                ("5", "Very poor", 0, 19.99, "Cannot perform yet; intensive support required"),
            ],
        },
        ("fr", "primary"): {
            "name": "Référentiel MINEDUB 2018 — Primaire Francophone",
            "domains": [
                ("C1", "Communication", None, [
                    "Communiquer oralement dans les deux langues officielles",
                    "Lire et comprendre des textes adaptés au niveau",
                    "Produire des écrits adaptés à des situations de communication",
                    "Pratiquer au moins une langue nationale selon le contexte scolaire",
                ]),
                ("C2", "Mathématiques, sciences et technologies", None, [
                    "Résoudre des situations-problèmes en utilisant des notions mathématiques",
                    "Mobiliser les nombres, opérations, mesures et grandeurs",
                    "Observer, questionner et expliquer des phénomènes scientifiques simples",
                    "Utiliser une démarche de recherche et de résolution de problème",
                ]),
                ("C3", "Valeurs sociales et citoyennes", None, [
                    "Respecter les règles, les droits et les devoirs dans la communauté",
                    "Coopérer, dialoguer et résoudre pacifiquement les conflits",
                    "Adopter des comportements responsables envers l'environnement",
                    "Démontrer respect, intégrité, solidarité et sens civique",
                ]),
                ("C4", "Autonomie, initiative, créativité et entrepreneuriat", None, [
                    "Organiser son travail et gérer progressivement son autonomie",
                    "Prendre des initiatives adaptées à une situation",
                    "Créer, proposer et améliorer une solution ou une production",
                    "Mobiliser des ressources pour réaliser une tâche ou un projet",
                ]),
                ("C5", "Technologies de l'information et de la communication", None, [
                    "Identifier et utiliser des outils numériques de base",
                    "Rechercher, sélectionner et exploiter une information avec accompagnement",
                    "Respecter les règles élémentaires de sécurité et de citoyenneté numérique",
                ]),
                ("C6", "Activités physiques et sportives", None, [
                    "Réaliser des mouvements et déplacements coordonnés",
                    "Participer à des activités sportives individuelles et collectives",
                    "Respecter les règles, consignes et partenaires dans le jeu",
                ]),
                ("C7", "Activités artistiques", None, [
                    "Produire et apprécier des réalisations artistiques",
                    "S'exprimer par le dessin, la musique, le chant, la danse ou le théâtre",
                    "Utiliser des techniques et matériaux artistiques adaptés",
                ]),
            ],
            "scales": [
                ("A+", "Expert", 90, 100, "Compétence définitivement installée"),
                ("A", "Acquis", 75, 89.99, "Compétence acquise"),
                ("ECA", "En cours d'acquisition", 50, 74.99, "Compétence en cours d'acquisition"),
                ("NA", "Non acquis", 0, 49.99, "Compétence non acquise"),
            ],
        },
        ("en", "primary"): {
            "name": "2018 MINEDUB Framework — Primary English",
            "domains": [
                ("C1", "Communication", None, [
                    "Communicate orally in the two official languages",
                    "Read and understand texts appropriate to the level",
                    "Produce written messages for appropriate communication situations",
                    "Practise at least one national language according to the school context",
                ]),
                ("C2", "Mathematics, Science and Technology", None, [
                    "Solve problems using mathematical concepts and procedures",
                    "Use numbers, operations, measurement and quantities appropriately",
                    "Observe, question and explain simple scientific phenomena",
                    "Use inquiry and problem-solving approaches",
                ]),
                ("C3", "Social and Civic Values", None, [
                    "Respect rules, rights and duties within the community",
                    "Cooperate, communicate and resolve conflicts peacefully",
                    "Demonstrate responsible behaviour towards the environment",
                    "Show respect, integrity, solidarity and civic responsibility",
                ]),
                ("C4", "Autonomy, Initiative, Creativity and Entrepreneurship", None, [
                    "Organise work and demonstrate increasing independence",
                    "Take appropriate initiative in a given situation",
                    "Create, propose and improve a solution or product",
                    "Mobilise resources to complete a task or project",
                ]),
                ("C5", "Information and Communication Technologies", None, [
                    "Identify and use basic digital tools",
                    "Find, select and use information with guidance",
                    "Respect basic digital safety and citizenship rules",
                ]),
                ("C6", "Physical and Sports Activities", None, [
                    "Perform coordinated movements and locomotor skills",
                    "Participate in individual and team physical activities",
                    "Respect rules, instructions and partners during games",
                ]),
                ("C7", "Arts", None, [
                    "Create and appreciate artistic productions",
                    "Express ideas through drawing, music, song, dance or drama",
                    "Use age-appropriate artistic techniques and materials",
                ]),
            ],
            # Valeurs par défaut configurables : la GPA est dérivée du
            # pourcentage global via cette échelle. Une école peut adapter
            # les seuils/points dans l'administration sans modifier le code.
            "scales": [
                ("A", "Excellent", 90, 100, "Outstanding performance", 4.0),
                ("B", "Very good", 80, 89.99, "Very good performance", 3.0),
                ("C", "Good", 70, 79.99, "Satisfactory/good performance", 2.0),
                ("D", "Pass", 60, 69.99, "Minimum satisfactory performance", 1.0),
                ("F", "Fail", 0, 59.99, "Performance below the passing threshold", 0.0),
            ],
        },
    }

    for (section, cycle), spec in definitions.items():
        f = db.query(EvaluationFramework).filter_by(
            school_id=school.id, school_year_id=year.id, section=section, cycle=cycle
        ).first()
        if f is None:
            f = EvaluationFramework(
                school_id=school.id, school_year_id=year.id, section=section,
                cycle=cycle, name=spec["name"], version="2018", active=True
            )
            db.add(f); db.flush()
        else:
            f.name = spec["name"]
            f.version = "2018"
            f.active = True

        for order, (code, label, weight, criteria_labels) in enumerate(spec["domains"], 1):
            d = db.query(EvaluationDomain).filter_by(framework_id=f.id, code=code).first()
            if d is None:
                d = EvaluationDomain(framework_id=f.id, code=code, name=label, weight=weight, display_order=order)
                db.add(d); db.flush()
            else:
                d.name, d.weight, d.display_order = label, weight, order

            # Upgrade the old one-criterion starter data without duplicating manually
            # created school criteria.
            existing = db.query(EvaluationCompetency).filter_by(domain_id=d.id).order_by(EvaluationCompetency.display_order).all()
            if len(existing) == 1 and existing[0].name == label and len(existing[0].criteria) <= 1:
                db.delete(existing[0]); db.flush(); existing = []
            if not existing:
                for cidx, criterion_label in enumerate(criteria_labels, 1):
                    c = EvaluationCompetency(domain_id=d.id, code=f"{code}.{cidx:02d}", name=criterion_label,
                                             description=criterion_label, display_order=cidx)
                    db.add(c); db.flush()
                    db.add(EvaluationCriterion(
                        competency_id=c.id, code=f"{code}.{cidx:02d}.01", label=criterion_label,
                        description=criterion_label, evaluation_mode="observation", display_order=1, max_score=20
                    ))

        # Ensure scale set matches the framework definition on a fresh seed or upgrade.
        existing_scales = {s.code: s for s in db.query(RatingScale).filter_by(framework_id=f.id).all()}
        wanted_codes = set()
        for order, scale_spec in enumerate(spec["scales"], 1):
            code, label, mi, ma, desc = scale_spec[:5]
            grade_point = scale_spec[5] if len(scale_spec) > 5 else None
            wanted_codes.add(code)
            s = existing_scales.get(code)
            if s is None:
                s = RatingScale(framework_id=f.id, code=code, label=label)
                db.add(s)
            s.label, s.min_percent, s.max_percent, s.description, s.grade_point, s.display_order = label, mi, ma, desc, grade_point, order
        for code, s in existing_scales.items():
            if code not in wanted_codes:
                db.delete(s)
    db.commit()


def _scrub_windows_initial_password() -> None:
    """Supprime le secret de première installation du .env persistant.

    Le mot de passe initial est nécessaire uniquement pour créer le premier
    compte administrateur. Après cette création, conserver le secret dans
    %PROGRAMDATA%\\SIGMA\\.env augmenterait inutilement l'impact d'une
    compromission locale du fichier de configuration.
    """
    try:
        from app.core.paths import data_dir
        env_path = data_dir() / ".env"
        if not env_path.exists():
            return
        lines = env_path.read_text(encoding="utf-8").splitlines()
        filtered = [line for line in lines if not line.startswith("SIGMA_INITIAL_ADMIN_PASSWORD=")]
        if filtered != lines:
            env_path.write_text("\n".join(filtered).rstrip() + "\n", encoding="utf-8")
    except OSError:
        # Le démarrage ne doit pas échouer si le fichier de configuration est
        # momentanément verrouillé; le secret reste alors protégé par les ACL
        # du dossier Windows et sera retiré au prochain démarrage.
        pass

def _write_initial_credentials_report(password: str):
    """Consigne le mot de passe d'amorçage dans le fichier d'identifiants.

    Retourne le chemin écrit, ou None si l'écriture est impossible (le secret
    est alors affiché en dernier recours pour ne pas rendre l'installation
    inutilisable).
    """
    try:
        from app.core.paths import data_dir
        report = data_dir() / "first-run-credentials.txt"
        report.write_text(
            "SIGMA — PREMIÈRE INSTALLATION\n\n"
            "Compte administrateur initial\n"
            "Utilisateur : admin\n"
            f"Mot de passe : {password}\n\n"
            "IMPORTANT : connectez-vous immédiatement et changez ce mot de passe.\n"
            "Ce fichier contient un secret : supprimez-le après la première connexion.\n",
            encoding="utf-8",
        )
        return report
    except OSError:
        return None


def run():
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    db = SessionLocal()
    try:
        print("Chargement du catalogue de permissions...")
        for code, module, label in PERMISSION_CATALOG:
            if not db.query(Permission).filter(Permission.code == code).first():
                db.add(Permission(code=code, module=module, label=label))
        db.commit()

        school = db.query(School).filter(School.name == "École Démo SIGMA").first()
        if school is None:
            print("Création de l'établissement de démonstration...")
            school = School(
                name="École Démo SIGMA",
                short_name="DEMO",
                language="fr",
                currency="XAF",
                grading_system="20",
                logo_path="/dashboard/assets/sigma-logo.jpg",
            )
            db.add(school)
            db.commit()
            db.refresh(school)

            year = AcademicYear(
                school_id=school.id, label="2026/2027",
                start_date=date(2026, 9, 1), end_date=date(2027, 7, 15),
                is_current=True,
            )
            db.add(year)
            db.commit()
            db.refresh(year)

            db.add_all([
                AcademicPeriod(academic_year_id=year.id, name="Trimestre 1", order_index=1,
                                start_date=date(2026, 9, 1), end_date=date(2026, 12, 15)),
                AcademicPeriod(academic_year_id=year.id, name="Trimestre 2", order_index=2,
                                start_date=date(2027, 1, 5), end_date=date(2027, 3, 25)),
                AcademicPeriod(academic_year_id=year.id, name="Trimestre 3", order_index=3,
                                start_date=date(2027, 4, 5), end_date=date(2027, 7, 15)),
            ])
            db.commit()

        year = db.query(AcademicYear).filter(AcademicYear.school_id == school.id, AcademicYear.is_current.is_(True)).first() or db.query(AcademicYear).filter(AcademicYear.school_id == school.id).order_by(AcademicYear.start_date.desc()).first()
        if year is None:
            year = AcademicYear(school_id=school.id, label="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 7, 15), is_current=True)
            db.add(year); db.commit(); db.refresh(year)
        seed_evaluation_frameworks(db, school, year)
        seed_appreciation_rules(db, school, year)

        default_template = db.query(CardTemplate).filter(
            CardTemplate.school_id == school.id, CardTemplate.is_default.is_(True)
        ).first()
        if default_template is None:
            print("Création du modèle de carte scolaire par défaut...")
            default_template = CardTemplate(
                school_id=school.id,
                name="Carte scolaire standard",
                card_type="student_id",
                layout={
                    "primary_color": "#11633A",
                    "accent_color": "#FF8A00",
                    "show_qr": True,
                    "show_photo": True,
                },
                is_default=True,
            )
            db.add(default_template)
            db.commit()

        admin = db.query(User).filter(User.username == "admin").first()
        # La variable d'environnement reste prioritaire (déploiements
        # automatisés), mais le cas normal sous Windows est le .env produit par
        # `run_server.py --setup`, lu ici via les settings.
        initial_password = os.getenv("SIGMA_INITIAL_ADMIN_PASSWORD") or settings.SIGMA_INITIAL_ADMIN_PASSWORD
        generated_password = False
        if admin is None:
            if not initial_password:
                # Aucun mot de passe partagé/fixe ne doit exister dans le code.
                # Un secret aléatoire est généré uniquement au premier démarrage
                # puis imposé au changement de mot de passe.
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                initial_password = "".join(secrets.choice(alphabet) for _ in range(24))
                generated_password = True
            print("Création de l'administrateur initial SIGMA...")
            admin = User(
                school_id=school.id,
                username="admin",
                # Pas d'email réel pour ce compte système : email=None (le
                # champ est nullable). Un email inventé sur un domaine
                # réservé (ex. .local, .test, .invalid — RFC 2606/6762)
                # plante systématiquement /api/auth/me, car email-validator
                # refuse ces domaines même en simple vérification de
                # syntaxe, et UserOut valide l'email en sortie via
                # EmailStr — voir aussi la correction sur UserOut plus bas
                # qui rend ce genre d'erreur non bloquant à l'avenir.
                email=None,
                hashed_password=hash_password(initial_password),
                first_name="Administrateur",
                last_name="Système",
                is_superadmin=True,
                must_change_password=True,
            )
            db.add(admin)
            db.commit()

        # Une fois l'administrateur initial effectivement présent, le secret
        # de bootstrap ne doit plus rester dans le .env persistant.
        if admin is not None and initial_password:
            _scrub_windows_initial_password()

        print("\nTerminé.")
        print(f"  École de démonstration: {school.name} (id={school.id})")
        if generated_password:
            # En build fenêtré, la sortie standard est redirigée vers
            # sigma-console.log : y imprimer le secret le rendrait persistant
            # dans un fichier de journal que personne ne pense à purger. On
            # l'écrit dans le fichier d'identifiants prévu pour cela, dont
            # l'installateur rappelle qu'il doit être supprimé.
            report = _write_initial_credentials_report(initial_password)
            if report is not None:
                print(f"  Compte initial -> username: admin | mot de passe enregistré dans: {report}")
                print("  ATTENTION : changez ce mot de passe à la première connexion, puis supprimez ce fichier.")
            elif not getattr(sys, "frozen", False):
                # Exécution depuis les sources, dans un vrai terminal : aucun
                # journal persistant n'est alimenté, l'affichage est sûr.
                print(f"  Compte initial -> username: admin | mot de passe: {initial_password}")
                print("  ATTENTION : changez ce mot de passe immédiatement après la première connexion.")
            else:
                # Build fenêtré : stdout est un fichier de journal. On n'y écrit
                # pas le secret ; on signale l'anomalie pour qu'elle soit
                # traitée plutôt que de laisser croire l'installation réussie.
                print("  ERREUR : impossible d'enregistrer les identifiants initiaux.")
                print("  Relancez l'installation avec SIGMA_INITIAL_ADMIN_PASSWORD défini.")
        elif initial_password:
            print("  Compte initial -> username: admin | mot de passe fourni par la configuration SIGMA.")
    finally:
        db.close()





def seed_appreciation_rules(db, school, year):
    """Règles de départ, entièrement modifiables par l'établissement."""
    frameworks = db.query(EvaluationFramework).filter(EvaluationFramework.school_id == school.id, EvaluationFramework.school_year_id == year.id).all()
    defaults = [
        ("EXCELLENT", 90, 100, "Excellent travail. Les acquis sont très solides et régulièrement mobilisés.", "Excellent work. Learning outcomes are very strong and consistently demonstrated."),
        ("TRES_SATISFAISANT", 80, 89.999, "Très bon travail. Les compétences sont bien maîtrisées.", "Very good work. Competencies are well mastered."),
        ("SATISFAISANT", 70, 79.999, "Travail satisfaisant. Les acquis sont globalement maîtrisés.", "Satisfactory work. Learning outcomes are generally mastered."),
        ("EN_PROGRES", 50, 69.999, "Des progrès sont visibles. Les efforts doivent être poursuivis.", "Progress is visible. Continued effort is needed."),
        ("A_RENFORCER", 0, 49.999, "Les acquis restent fragiles. Un accompagnement renforcé est recommandé.", "Learning outcomes remain fragile. Additional support is recommended."),
    ]
    for framework in frameworks:
        if db.query(AppreciationRule).filter(AppreciationRule.framework_id == framework.id).count():
            continue
        for i, (code, lo, hi, fr, en) in enumerate(defaults, 1):
            db.add(AppreciationRule(framework_id=framework.id, code=code, min_percent=lo, max_percent=hi, text_fr=fr, text_en=en, priority=i))
    db.commit()


if __name__ == "__main__":
    run()
