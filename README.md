# SIGMA V4.46.0 — Production Hardening H4 & Android

SIGMA V4.46.0 renforce la chaîne de mise à jour avec des manifestes Ed25519 et ajoute un projet Android natif ainsi qu'un pipeline CI de compilation APK.

## V4.46.0 — H4 Reliability & Security Gate

- Extraction ZIP des mises à jour durcie contre traversal, symlinks et archives à décompression excessive.
- Agent de mise à jour : HTTP non chiffré refusé ; verrou de mise à jour récupérable si le processus précédent est mort.
- Rate limiter mémoire borné pour éviter une croissance incontrôlée du nombre de clés.
- Authentification : coût cryptographique comparable sur identifiant inexistant et compte réel ; limitation IP + identité ; état de verrouillage non divulgué.
- Dossier Élève 360 : filtre d'année scolaire réellement appliqué aux notes.
- Campagnes de communication : suppression d'un N+1 lors de la résolution des responsables.
- Gateway SMS : journalisation d'erreur corrigée.


- Finance `Decimal/NUMERIC(14,2)` + idempotence transactionnelle des paiements.
- Notes finales limitées aux états `validated/locked/published`.
- Échelle anglaise A/B/C/D/F avec grade points/GPA configurables.
- QR signés pour vérifier publiquement bulletins et reçus sans exposer les données sensibles.
- Manifestes de mise à jour signés Ed25519 avec `key_id`.
- Vérification fail-closed dans l'agent de mise à jour.
- SHA-256 et taille exacte de l'artefact toujours vérifiés après authentification du manifeste.
- Projet Android dans `mobile/android`.
- HTTPS obligatoire, contenu mixte bloqué, navigation WebView restreinte au serveur SIGMA.
- Compilation CI automatique d'une APK debug installable.
- Compilation release signée prévue via secrets de keystore GitHub Actions.
- Le SDK Android/Gradle n'étant pas installé dans l'environnement local actuel, la compilation APK réelle doit être exécutée dans GitHub Actions ou sur un poste Android SDK 35.

## Qualification H2-H4

- Migrations Alembic qualifiées jusqu'à `20260920_6200` sur base SQLite neuve.
- Concordance ORM/DB : 86 tables modèle, 87 tables DB avec `alembic_version`, aucune colonne manquante/excédentaire hors table Alembic.
- Tests ciblés H2-H4 : 23/23 PASS sur le lot exécuté.
- La suite complète reste à exécuter dans CI avec toutes les dépendances runtime.

## V4.40
- inventaire centralisé des installations ;
- heartbeat par instance ;
- détection de dérive de version ;
- suivi santé/sauvegarde/synchronisation ;
- planification canary/progressive ;
- arrêt automatique d'un rollout lorsque le seuil d'échec est dépassé.

> Le rollout décrit l'état et les garde-fous ; l'application distante de l'artefact reste effectuée par l'agent/deployeur sécurisé existant.

# État de qualification V4.46.0

> **État actuel :** V4.46.0 — hardening sécurité, finance décimale, idempotence paiements, index haute charge, moteur académique borné aux résultats validés, rate limiting Redis optionnel et file offline Android ACK. La certification environnementale réelle Windows/PostgreSQL/Android reste obligatoire avant production.

## V4.34 en bref

- `/api/health/live` : liveness minimal.
- `/api/health/ready` : readiness avec base, stockage et métriques de service.
- `scripts/health_probe.py` : sonde automatisable.
- `scripts/auto_heal.py` : redémarrage borné du service Windows, avec cooldown.
- `scripts/deploy_safe.py` + `app/services/deployment_guard.py` : activation protégée, vérification de santé et rollback.
- Le zéro-downtime strict n’est pas promis pour une instance Windows unique ; il nécessite plusieurs instances derrière un proxy/load balancer.



Le protocole de synchronisation supporte désormais les créations offline contrôlées des élèves et responsables avec correspondance identifiant client/serveur.

# SIGMA — Système Intégré de Gestion et Management Académique

Serveur d'une version **MVP avancée et orientée commercialisation** de la plateforme
de gestion scolaire SIGMA, conforme au cahier des charges v2.1 : moteur
d'habilitation séparé des fonctionnalités, architecture multi-établissement,
notes avec cycle d'états, finance tracée, cartes d'accès, SMS via le boîtier
de l'établissement, et tableau de bord dynamique.

**Base de données : SQLite par défaut.** Aucune installation de serveur de
base de données requise — un simple fichier `sigma.db` est créé
automatiquement. PostgreSQL reste disponible en changeant une seule variable
d'environnement, pour quand l'établissement grandit (voir plus bas).

## SIGMA V4.31 — PostgreSQL & Concurrency Qualification

La version V4.31 ajoute la qualification de portabilité PostgreSQL et de concurrence, tout en conservant les contrôles de sauvegarde/restauration V4.30. La validation d’un serveur PostgreSQL réel reste un gate environnemental si aucun serveur n’est disponible.

La version V4.30 durcit la sauvegarde et la restauration : intégrité SQLite, manifeste exhaustif, limites de taille, anti-duplication ZIP, confinement des chemins et protection des uploads de restauration. Voir `docs/RELEASE_4.30.md`.

## SIGMA V4.22 — Payment Gateway Core

Le serveur dispose désormais d'un socle de paiement externe sécurisé : webhook signé HMAC-SHA256, contrôle d'âge, idempotence des événements et rapprochement avec les factures d'abonnement. Les intégrations spécifiques aux fournisseurs Mobile Money/PSP restent volontairement séparées afin de respecter leurs contrats API et exigences de sécurité.

## SIGMA V4.17 — Portails Parent & Enseignant

La plateforme inclut désormais deux espaces dédiés : `/dashboard/parent.html` et `/dashboard/teacher.html`, avec APIs sécurisées `/api/parent/*` et `/api/teacher/overview`.

## Ce qui est livré

| Bloc | Contenu |
|---|---|
| **Infrastructure** | API REST FastAPI + SQLite (ou PostgreSQL), JWT, Docker |
| **Bloc 1 — Administration** | Établissements, années/périodes scolaires, utilisateurs, postes configurables, permissions scopées, délégations temporaires, journal d'audit |
| **Bloc 2 — Élèves** | Dossiers élèves, niveaux/séries/classes, tuteurs, inscriptions avec historique préservé (redoublements) |
| **Bloc 3 — Académique** | Matières, affectations enseignants, évaluations, notes (cycle brouillon → publié), moteur de calcul de moyennes/classements, génération de bulletins |
| **Bloc 4 — Finance** | Grilles de frais, factures, paiements, reçus numérotés, annulation tracée (jamais de suppression physique) |
| **Cartes d'accès** | Modèles de carte éditables (couleurs, champs), émission/révocation, QR code d'accès, impression HTML (unitaire ou classe entière), point de vérification pour un lecteur de badge |
| **Communication / SMS** | Envoi via le "boîtier" SMS de l'établissement (driver HTTP configurable, ou mode "fake" journalisé pour tourner sans matériel), envoi ciblé par classe ou par impayés, journal + reprise sur échec |
| **Effectif** | Rapport consolidé par niveau/classe/sexe, taux de remplissage |
| **Photos élèves** | Bouton d'import de photo directement dans la grille élèves (`/dashboard/students.html`), normalisation automatique (orientation, taille) via Pillow |
| **Excel** | Export de la liste des élèves (.xlsx), gabarit d'import vierge à distribuer, import en masse avec validation ligne par ligne (une ligne invalide n'annule pas les autres) |
| **PDF** | Export de la liste des élèves, bulletin individuel, bulletins de toute une classe en un seul PDF — génération pure Python (reportlab), aucune dépendance système |
| **Bloc 6 — Pilotage** | Tableau de bord dynamique (page web autonome avec graphiques, auto-actualisation) + API d'indicateurs + alertes intelligentes |
| **Interface** | 7 pages web (charte SIGMA, sans build) couvrant tout ce qui précède : tableau de bord, élèves, académique, finance, cartes, communication, administration |

**Limites actuelles** : paie/RH complet, portails web/mobile riches
(le socle API existe, mais le frontend dédié reste à finaliser), synchronisation
Cloud externe et multisite complet. Le mode offline/online local est désormais
implémenté progressivement : identités offline (2.0) puis inscriptions
synchronisables (2.1), avec contrôles d'identité, de version et de conflit.

## Démarrage rapide (développement)

**Windows :**
```bat
setup.bat
```

**macOS / Linux :**
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_server.py --setup
python -m alembic upgrade head
python run_server.py
```

`setup.bat` crée l'environnement Python, installe les dépendances, génère la
configuration locale (`.env`) et applique les migrations. Il ne démarre pas le
serveur : lancez ensuite `OUVRIR_SIGMA.vbs` (double-clic) ou
`.venv\Scripts\python run_server.py`.

**Version de Python recommandée : 3.11, 3.12 ou 3.13.** Évitez pour
l'instant la toute dernière version sortie (ex: 3.14 à sa sortie) : certaines
dépendances (Pillow, pydantic) n'ont pas encore de version précompilée pour
elle, ce qui force une compilation depuis les sources et échoue sans
outils de compilation installés (Rust, Visual Studio Build Tools...). Le
script vous préviendra clairement si c'est le cas et vous rappellera cette
solution.

- API + documentation interactive : http://localhost:8000/docs
- **Tableau de bord** : http://localhost:8000/dashboard/
- Identifiants initiaux : utilisateur `admin`, mot de passe **généré
  cryptographiquement aléatoire** à la première installation. Il est écrit dans
  `first-run-credentials.txt`, à côté des données
  (`%PROGRAMDATA%\SIGMA` en installation Windows, sinon la racine du projet).
  ⚠️ Changez-le à la première connexion, puis supprimez ce fichier.

Pour relancer le serveur une fois l'installation faite, `setup.bat` détecte que
l'environnement existe déjà et va directement aux vérifications.

<details>
<summary>Étapes manuelles (si vous préférez ne pas utiliser le script)</summary>

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn app.main:app --reload
```
</details>

## Démarrage avec Docker (alternative)

```bash
docker compose up --build
```
Construit l'image, crée le volume SQLite persistant, initialise la base et
lance l'API sur `http://localhost:8000`. Le tableau de bord est accessible
au même endroit : `http://localhost:8000/dashboard/`.

## Compiler en exécutable autonome (.exe) pour installer sur une machine

Pour distribuer SIGMA à un établissement sans que quiconque ait besoin
d'installer Python, vous pouvez compiler un exécutable autonome qui embarque
tout (Python compris) — un simple dossier à copier, un double-clic pour
démarrer.

**Étapes (à faire une fois, sur votre poste de développement) :**

Sur Windows, tout est automatisé et **aucune commande n'est à saisir** :
double-cliquez sur `BUILD_SIGMA_WINDOWS.vbs`. Le script installe au besoin
Python 3.13 et Inno Setup (via winget), crée un environnement isolé, installe
les dépendances, joue les tests, compile avec PyInstaller, exécute un test de
fumée sur l'exécutable produit, puis construit `SIGMA-Setup.exe`.

Pour un usage en ligne de commande :

```powershell
# Paquet complet (portable + installateur)
powershell -ExecutionPolicy Bypass -File build_windows.ps1 -Clean

# Paquet portable seulement (sans Inno Setup)
powershell -ExecutionPolicy Bypass -File build_windows_portable.ps1 -Clean
```

Le résultat se trouve dans `dist/SIGMA-Server/` : un dossier complet
(exécutable + toutes ses dépendances + l'interface web). **Copiez ce dossier
en entier** sur la machine de l'établissement (clé USB, partage réseau...) —
l'exécutable seul ne suffit pas, il a besoin des fichiers à côté de lui.

**Sur la machine cible :** double-cliquez sur `SIGMA-Server.exe`. Aucune
installation de Python n'est nécessaire. L'exécutable est compilé sans console
(`console=False`) : rien ne s'affiche, le serveur démarre en arrière-plan puis
le navigateur par défaut s'ouvre tout seul sur le tableau de bord. Les journaux
sont écrits dans `sigma-console.log`, dans le dossier de données.

La base de données (`sigma.db`), les photos importées (`media/`) et la
configuration (`.env`) sont créées dans `%PROGRAMDATA%\SIGMA` et **non** à côté
de l'exécutable : elles survivent ainsi aux mises à jour et n'exigent pas de
droits d'écriture dans `Program Files`. Pour un usage réellement nomade (clé
USB), définissez la variable d'environnement `SIGMA_DATA_DIR` sur le dossier
voulu.

Pour arrêter un serveur portable, double-cliquez sur `ARRETER_SIGMA.vbs` (ou
lancez `SIGMA-Server.exe --stop`) : l'arrêt est normal, pas forcé — les
connexions et la base sont refermées proprement. En installation commerciale,
le serveur est un service Windows, arrêtez-le depuis `services.msc`.

Le mode service Windows impose la compilation **onedir** (un dossier) plutôt
que **onefile** (un fichier unique) : en onefile, le bootloader PyInstaller
relance l'application dans un processus enfant, que le Gestionnaire de services
ne surveille pas — le service échoue alors avec l'erreur 1053.

Points d'attention :
- **Antivirus** : les exécutables générés par PyInstaller déclenchent parfois
  une fausse alerte à la première exécution (heuristique générique, pas une
  détection réelle). C'est un faux positif connu et documenté du projet
  PyInstaller ; ajoutez une exception si besoin.
- **Réseau local** : le serveur est configuré pour écouter sur `0.0.0.0:8000`. Les autres postes de l'intranet peuvent donc rejoindre le serveur si le pare-feu autorise le port 8000. Les appareils clients disposent désormais d'un identifiant et d'un heartbeat.
- **Ce n'est pas encore un service Windows** : la fenêtre de console doit
  rester ouverte. Le cahier des charges prévoit un vrai service système
  (démarrage automatique, pas de fenêtre à garder ouverte) — c'est une
  prochaine étape logique (voir plus bas), pas encore fait dans cette phase.

## Architecture du code


```
sigma/
├── app/
│   ├── core/          # config, chemins (dev/.exe), connexion DB, sécurité (JWT, hash)
│   ├── models/         # tables SQLAlchemy (une entité = un fichier par domaine)
│   ├── schemas/        # schémas Pydantic (validation entrée/sortie API)
│   ├── services/
│   │   ├── authorization.py   # LE moteur d'habilitation (RBAC + scopes + délégations)
│   │   ├── grading_engine.py  # calcul des moyennes et classements
│   │   ├── card_engine.py     # rendu HTML des cartes + QR code
│   │   ├── sms_gateway.py     # abstraction du boîtier SMS (driver "fake"/"http")
│   │   └── audit.py           # écriture dans le journal d'audit
│   ├── api/             # routeurs FastAPI (un fichier par module métier)
│   ├── deps.py           # dépendances FastAPI (utilisateur courant, require_permission)
│   └── main.py           # assemblage de l'application + montage du tableau de bord
├── static/
│   ├── assets/
│   │   ├── sigma.css      # design system partagé (charte graphique)
│   │   ├── sigma.js       # auth, appel API, barre de contexte, navigation
│   │   └── sigma-logo.jpg
│   ├── index.html            # tableau de bord dynamique
│   ├── students.html          # grille élèves (photos, import/export)
│   ├── academic.html          # notes, classements, bulletins
│   ├── finance.html           # frais, factures, paiements, reçus
│   ├── cards.html              # cartes d'accès
│   ├── communication.html      # SMS
│   └── administration.html     # structure, utilisateurs, postes, audit
├── alembic/              # migrations de base de données
├── seed.py               # catalogue de permissions + école/admin de démo
├── setup.bat             # préparation technique du pilote (développement)
├── run_server.py         # point d'entrée: console, portable et service Windows
├── sigma.spec            # configuration PyInstaller (mode onedir)
├── build_windows.ps1     # compilation complète: tests, exe, smoke test, installateur
├── build_windows_portable.ps1  # compilation du paquet portable seul
├── BUILD_SIGMA_WINDOWS.vbs     # compilation par simple double-clic
├── installer/SIGMA-Setup.iss   # installateur Inno Setup + service Windows
├── tools_release_gate.py       # contrôle de cohérence de version avant build
├── requirements.txt          # dépendances (SQLite inclus nativement dans Python)
└── requirements-build.txt    # dépendances additionnelles pour compiler et tester
```

### Le moteur d'habilitation (le cœur du système)

Conformément à la règle d'or du cahier des charges, **le code définit des
permissions atomiques** (ex. `academic.grades.enter`, `finance.payments.cancel`,
`cards.issue`, `communication.sms.send`) mais **ne décide jamais lui-même qui
peut les exercer**. C'est `app/services/authorization.py` qui répond à la
question à l'exécution, en croisant :

1. les **postes** de l'utilisateur (`UserPost`) — un utilisateur peut en avoir plusieurs ;
2. les **permissions** attachées à chaque poste (`PostPermission`), chacune
   avec un **périmètre** JSON optionnel (`{"class_id": 12, "subject_id": 3}`) ;
3. les **délégations temporaires** actives (`Delegation`), qui expirent
   automatiquement à la date de fin.

Un périmètre vide `{}` = accès à tout l'établissement.

### Cycle de vie d'une note

```
draft → submitted → checked → validated → locked → published
```
Chaque transition est historisée. Une fois `locked`, toute écriture directe
est refusée par l'API (HTTP 409).

### Traçabilité financière

Un paiement n'est **jamais supprimé** : `POST /api/payments/{id}/cancel` le
marque annulé avec un motif obligatoire, journalisé dans `audit_logs`. Chaque
réimpression de reçu incrémente un compteur pour rester identifiable.

### Cartes d'accès

Les modèles de carte (`CardTemplate`) sont éditables sans toucher au code :
couleurs, champs affichés, activation du QR/de la photo (`PATCH
/api/card-templates/{id}`). Une carte émise (`IdCard`) porte un `access_code`
unique encodé dans un QR — le endpoint `GET /api/id-cards/verify/{access_code}`
sert de point de contrôle pour un lecteur/scanner de badge au portail.

Impression : `GET /api/id-cards/{id}/print` (une carte) ou
`GET /api/classes/{class_id}/id-cards/print` (toute une classe) renvoient une
page HTML prête à imprimer (Ctrl+P → « Enregistrer en PDF » depuis le
navigateur). Si le paquet optionnel `qrcode` est installé (il l'est par
défaut dans `requirements.txt`), un vrai QR code est intégré ; sinon la carte
reste utilisable avec le code affiché en texte.

### SMS via le boîtier

Le "boîtier" (box GSM / téléphone Android en passerelle SMS / modem) varie
d'un établissement à l'autre. `app/services/sms_gateway.py` expose une petite
interface `SmsDriver` avec :

- **mode `fake`** (par défaut) : n'envoie rien de réel, journalise chaque
  tentative — SIGMA fonctionne donc immédiatement, avant même le branchement
  du boîtier physique.
- **mode `http`** : envoie une requête `POST` à l'adresse locale du boîtier
  (`SMS_GATEWAY_URL` dans `.env`), au format `{"to", "text", "sender"}` avec
  une clé API optionnelle — le protocole le plus courant pour les boîtiers
  SMS Android et la plupart des box GSM commerciales.

Pour un boîtier au protocole différent (commandes AT sur port série, API
propriétaire), ajoutez une classe implémentant `SmsDriver.send()` dans
`sms_gateway.py` et sélectionnez-la dans `get_driver()`.

Endpoints : `POST /api/sms/send` (numéro unique), `POST
/api/sms/send-to-class` (« tous les parents de 3e C »), `POST
/api/sms/send-to-unpaid` (« parents dont les frais sont impayés » — exemples
directement issus du cahier des charges §33), `GET /api/sms/logs`, `POST
/api/sms/{id}/retry`.

### Tableau de bord dynamique

`static/index.html` est une page autonome (HTML/JS + Chart.js via CDN, aucun
outil de build) servie sur `/dashboard/`. Elle se connecte avec les
identifiants SIGMA, puis affiche : effectifs, personnel, classes, taux de
recouvrement, moyenne générale, taux de réussite, taux d'absentéisme,
répartition de l'effectif par niveau/sexe (graphique), évolution de la
moyenne d'une classe, répartition financière encaissé/restant dû, et les
alertes intelligentes — le tout auto-actualisé toutes les 30 secondes.

### Grille élèves : photos, import et export

`static/students.html` (accessible depuis `/dashboard/students.html`, lien
"Élèves" dans l'en-tête) affiche la liste des élèves avec recherche, filtre
par classe et pagination. Chaque ligne a une vignette photo cliquable :
cliquer dessus ouvre le sélecteur de fichier et envoie directement la photo
au serveur (`POST /api/students/{id}/photo`), qui la valide et la normalise
(orientation EXIF corrigée, redimensionnée, recompressée en JPEG) via
Pillow.

Boutons dédiés :
- **Modèle d'import Excel** (`GET /api/students/import/template.xlsx`) :
  classeur vierge avec les colonnes attendues, à distribuer au secrétariat.
- **Importer un fichier Excel** (`POST /api/students/import`) : création en
  masse, avec un rapport détaillé (créés / matricules déjà existants
  ignorés / lignes en erreur avec le numéro de ligne et la raison) — une
  ligne invalide ne bloque jamais l'import des autres.
- **Exporter Excel** (`GET /api/students/export.xlsx`) et **Exporter PDF**
  (`GET /api/students/export.pdf`) : liste complète, mise en forme, prête à
  archiver ou imprimer.

Les bulletins bénéficient du même traitement PDF : `GET
/api/report-cards/{id}/pdf` (un élève) et `GET
/api/classes/{class_id}/report-cards/pdf?academic_period_id=...` (toute une
classe en un seul fichier, un bulletin par page).

### Interface complète (`/dashboard/`)

Sept pages statiques (HTML/JS, aucun build, même approche que le tableau de
bord), toutes à la charte SIGMA (couleurs, typographie Exo 2/Montserrat,
logo) et partageant un même design system (`static/assets/sigma.css` et
`static/assets/sigma.js`) : connexion unique, notifications, et une **barre
de contexte** commune (école → année → classe → période, en cascade) dont la
sélection est mémorisée d'une page à l'autre.

| Page | Contenu |
|---|---|
| `index.html` | Tableau de bord dynamique |
| `students.html` | Grille élèves, photos, création, import/export Excel/PDF |
| `academic.html` | Matières, création d'évaluations, saisie des notes (grille éditable), cycle d'états, classement, génération/publication/export PDF des bulletins |
| `finance.html` | Grille de frais, recherche élève, factures, paiements, reçus PDF, annulation |
| `cards.html` | Modèles de carte (couleurs, QR, photo), émission, révocation, impression |
| `communication.html` | Envoi de SMS (numéro, classe, impayés), historique, reprise sur échec |
| `administration.html` | Établissements/années/périodes/niveaux/séries/classes, utilisateurs, postes et permissions (avec périmètre), délégations temporaires, journal d'audit |

Chaque action y appelle directement l'API décrite plus haut — l'interface
n'ajoute aucune logique métier, elle ne fait qu'exposer proprement ce qui
existe déjà côté serveur.

## Faire évoluer le schéma (Alembic)

Le démarrage rapide crée les tables directement via `seed.py`
(`Base.metadata.create_all`). Pour un usage en production avec des
migrations versionnées :

```bash
alembic revision --autogenerate -m "état initial"
alembic upgrade head
```

## Passer de SQLite à PostgreSQL

Quand l'établissement grandit (plusieurs serveurs, gros volumes, accès
concurrents intensifs) :

```bash
pip install -r requirements-postgres.txt
```
puis dans `.env` :
```
DATABASE_URL=postgresql+psycopg://sigma:sigma@localhost:5432/sigma
```
Le profil inclut le driver `psycopg` ainsi que le reste des dépendances applicatives. En environnement cloud, PostgreSQL est la cible recommandée pour plusieurs workers/instances.
Aucune autre modification de code n'est nécessaire : SQLAlchemy et Alembic
gèrent les deux moteurs de façon transparente.

## Exemple de flux d'utilisation (curl)

```bash
# 1. Connexion
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=$MOT_DE_PASSE_INITIAL" | jq -r .access_token)

# 2. Créer un élève
curl -X POST http://localhost:8000/api/students \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"school_id": 1, "matricule": "00452", "first_name": "Grâce", "last_name": "Ebomo"}'

# 3. Émettre sa carte scolaire (modèle par défaut créé par seed.py, id=1)
curl -X POST http://localhost:8000/api/id-cards \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"school_id": 1, "template_id": 1, "holder_type": "student", "student_id": 1}'

# 4. Envoyer un SMS de test (mode "fake": journalisé, aucun envoi réel)
curl -X POST http://localhost:8000/api/sms/send \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"school_id": 1, "phone": "+237600000000", "body": "Bienvenue sur SIGMA"}'

# 5. Importer la photo de l'élève
curl -X POST http://localhost:8000/api/students/1/photo \
  -H "Authorization: Bearer $TOKEN" -F "file=@photo_grace.jpg"

# 6. Exporter la liste des élèves en Excel puis en PDF
curl -o eleves.xlsx "http://localhost:8000/api/students/export.xlsx?school_id=1" -H "Authorization: Bearer $TOKEN"
curl -o eleves.pdf  "http://localhost:8000/api/students/export.pdf?school_id=1"  -H "Authorization: Bearer $TOKEN"
```

## Prochaines étapes suggérées

1. **Frontend mobile/PWA natif** pour enseignants et parents — l'API de synchronisation est maintenant structurée pour les usages offline/online.
2. **Service Windows** : finaliser l'exécution automatique au démarrage, sans fenêtre de console, avec supervision et reprise après incident.
3. **Durcissement réseau multi-postes** : HTTPS local optionnel, règles pare-feu, découverte/identification des postes et supervision des appareils synchronisés.
4. **Synchronisation avancée** : résoudre les conflits métier avec interface de rapprochement et poursuivre la couverture des domaines hors élèves/inscriptions/notes.
5. **RH & paie**, **discipline avancée** et enrichissement des **tableaux d'honneur automatisés**.
6. **Durcissement production** : rotation des secrets, 2FA, sauvegardes chiffrées planifiées et tests HTTP/E2E sur environnement équipé des dépendances.

## Note sur cette livraison

La version 2.20.0 a été vérifiée automatiquement avant archivage. Les contrôles réalisés sont :
- `python -m compileall -q app seed.py run_server.py` : **OK** ;
- suite `pytest -q` : **60 tests réussis** ;
- `alembic heads` : **20260913_2500** (aucune migration serveur requise pour cette étape client) ;
- contrôle de l'archive ZIP après construction : **OK** ;
- vérification statique des routes et du protocole de synchronisation : **OK**.

Un démarrage HTTP complet et un test navigateur réel n'ont pas été déclarés comme vérifiés dans cet environnement, notamment parce que la dépendance `bcrypt` n'est pas installée dans l'environnement d'analyse. Cela ne remet pas en cause les contrôles de syntaxe et la suite de tests qui ne nécessitent pas cet import.

La version 2.4 ajoute le transport synchronisé des transitions d'état des notes, avec circuit séquentiel, audit, permissions dédiées et protection des périodes clôturées.


## Correctifs MVP intégrés
- Persistance renforcée : création automatique des tables au démarrage et compatibilité SQLite pour les nouvelles colonnes.
- Fiche élève complète : identité, naissance, quartier, classe, niveau/section déduits, parent/tuteur et téléphone.
- Téléversement de photo depuis la fiche et la liste.
- Retrait d’un élève des effectifs : fermeture de son affectation courante et conservation de l’historique.
- Tableau de bord dynamique sans dépendance Chart.js/Internet : indicateurs, barres d’effectifs, évolution, actualisation automatique et export PDF.
- Administration sécurisée des établissements, niveaux, séries et classes avec validation des appartenances.
- Établissement : logo, deux contacts téléphoniques, e-mail, timbre officiel et intitulé du ministère pour les documents/cartes.
- Communication SMS ciblée vers un parent/tuteur, une classe, un niveau, une section/série ou tout l’établissement.
- Cartes d’accès téléchargeables en PDF individuellement ou en lot par classe, avec photo, identité, classe, téléphone parent, quartier, logo, contacts et timbre si fourni.
- Module Finance retiré de la navigation du MVP (les modèles/API restent présents pour une réintégration ultérieure).
- Serveur lancé sur `0.0.0.0` pour permettre l’accès depuis les autres PC de l’intranet.


## Module Évaluations & Carnets — SIGMA Édition Maternelle & Primaire

Cette version ajoute un moteur de référentiels d'évaluation configurable pour les écoles maternelles et primaires francophones et anglophones.

- 4 référentiels de départ: Maternelle FR/EN, Primaire FR/EN
- Domaines, compétences, critères, échelles de cotation configurables
- Évaluations par observation, oral, écrit, pratique ou projet
- Résultats individuels avec observation, points forts et besoins d'accompagnement
- Cotation primaire A+/A/ECA/NA et gestion distincte de la maternelle
- Génération PDF du carnet/bulletin à partir du référentiel actif
- Page web `/dashboard/evaluations.html`

Les référentiels de départ sont des configurations initiales inspirées du cadre MINEDUB 2018; ils restent modifiables par l'établissement.


## Release courante
**v2.10.0-primary-commercial** — intégration du moteur offline à un client HTTP: push/apply/pull, cache local de consultation, ACK, reprise réseau et conservation durable des opérations.


## Release 1.8.0 — Synchronisation contrôlée

La file de synchronisation dispose désormais d’une validation contrôlée, d’une idempotence renforcée et d’un versionnement logique des entités. L’application automatique des mutations métier reste volontairement séparée et sera introduite avec des handlers dédiés.
## SIGMA V3.8 — Cloud commercial

- Licence et abonnement par établissement (`school_subscriptions`)
- Etat Cloud : plan, statut, échéance, quotas et fonctionnalités
- Evénements Cloud pour la traçabilité des changements de licence
- Intégrité du journal d’audit par chaîne SHA-256
- Renforcement du cloisonnement multi-école sur les endpoints organisationnels
- Superadministrateur requis pour les opérations de groupe et la modification d’une licence


## SIGMA V3.9 — Production & Exploitation

Cette version ajoute la couche d'exploitation production :

- endpoints liveness/readiness ;
- diagnostic de la base de données et du stockage ;
- contrôle de fraîcheur des sauvegardes ;
- posture de sécurité ;
- identifiant de requête `X-Request-ID` ;
- en-têtes HTTP de durcissement ;
- refus du démarrage en environnement `production` sans `SECRET_KEY` ;
- permission `administration.system.view` pour les diagnostics détaillés.

Commande recommandée pour la validation : `PYTHONPATH=. pytest -q`.


## V4.4 — Operations

SIGMA V4.4 ajoute une supervision système, la rotation contrôlée des sauvegardes et la validation hors exécution des packages de mise à jour. Voir `docs/RELEASE_4.4.md`.

## SIGMA V4.18 — Onboarding établissement
Cette version ajoute un état d'onboarding persistant et un bootstrap contrôlé pour préparer une école : année scolaire, périodes, profils RBAC, abonnement et checklist de mise en service.

## V4.21 — Performance & Observability Enterprise

La V4.21 ajoute la mesure légère des performances HTTP (p50/p95/p99, erreurs 5xx, routes lentes) via `/api/system/performance/metrics`, protégée par `administration.operations.view`, ainsi que le réglage du pool PostgreSQL. Les métriques ne stockent ni corps de requête, ni tokens, ni mots de passe.

## V4.19 — Production & SaaS Control Center

Ajouts : `PlatformIncident`, `PlatformMetricSnapshot`, service/API Control Center, gestion d'incidents cloisonnée, snapshots de métriques et interface `/dashboard/operations.html`.

Validation fonctionnelle V4.x : 45 tests ciblés passés. Compilation Python OK. La chaîne Alembic historique complète reste à industrialiser : elle part d'un historique V2 qui ne contient pas de migration initiale du schéma `schools`; la validation d'installation neuve doit donc être traitée comme chantier séparé et ne doit pas être déclarée résolue.
