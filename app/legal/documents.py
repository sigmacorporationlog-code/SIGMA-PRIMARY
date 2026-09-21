from datetime import date

COMMON = """SIGMA est un logiciel de gestion d'établissement scolaire édité par [ÉDITEUR SIGMA]. Les champs entre crochets doivent être complétés avant signature ou mise en production. Ce modèle constitue une base contractuelle et doit être relu et adapté par un conseil juridique compétent avant utilisation commerciale définitive."""

LICENSE = f"""# CONTRAT DE LICENCE ET D'ABONNEMENT SIGMA

Version : 1.0 — Date d'effet : 14/09/2026

{COMMON}

## 1. Parties
Éditeur : [RAISON SOCIALE], [forme juridique], [RCCM/NIU], [adresse], [email].
Client : [ÉTABLISSEMENT], représenté par [NOM, QUALITÉ], [adresse], [email].

## 2. Objet
L'Éditeur concède au Client un droit non exclusif, non cessible et limité à la durée souscrite d'utiliser SIGMA pour la gestion de son ou ses établissements autorisés.

## 3. Licence et périmètre
Le plan, le nombre maximal d'utilisateurs, le nombre maximal d'élèves, les modules et la durée figurent sur le bon de commande ou la fiche d'abonnement. Toute extension doit être autorisée et facturée selon le tarif en vigueur.

## 4. Compte et sécurité
Le Client est responsable de ses comptes, mots de passe, habilitations et postes. Il doit signaler sans délai tout accès suspect ou compromission.

## 5. Données
Le Client reste responsable des données scolaires qu'il introduit. L'Éditeur fournit les moyens techniques nécessaires au traitement conformément à la politique de confidentialité et aux instructions documentées du Client.

## 6. Disponibilité et maintenance
L'Éditeur peut effectuer des maintenances planifiées et des mises à jour de sécurité. Les modalités de disponibilité et de support sont précisées dans l'offre souscrite.

## 7. Paiement
Les montants, périodicité, échéances, taxes et moyens de paiement sont ceux figurant sur la facture ou le bon de commande. Les impayés peuvent entraîner une suspension après notification et, le cas échéant, après une période de grâce contractuelle.

## 8. Propriété intellectuelle
SIGMA, son code, son interface, sa documentation et ses éléments graphiques restent la propriété de l'Éditeur ou de ses concédants. Le Client reçoit uniquement les droits expressément accordés.

## 9. Sauvegardes et restitution
L'Éditeur applique une politique de sauvegarde définie dans la documentation de service. À la fin du contrat, les modalités de restitution et de suppression des données sont celles prévues par l'offre et la politique de conservation.

## 10. Responsabilité
Chaque partie répond de ses obligations. SIGMA est un outil de gestion et d'aide au pilotage ; il ne remplace pas les décisions pédagogiques, administratives, financières ou juridiques du Client.

## 11. Résiliation
Le contrat peut être résilié selon les conditions prévues au bon de commande. Les obligations de confidentialité, propriété intellectuelle, paiement et protection des données survivent lorsque leur nature l'exige.

## 12. Droit applicable et règlement des différends
Le droit applicable, la juridiction compétente et toute clause de médiation/arbitrage doivent être complétés par l'Éditeur après validation juridique locale.

## 13. Acceptation électronique
L'acceptation électronique horodatée, associée au compte habilité du représentant du Client, peut être conservée comme preuve de l'acceptation de la version indiquée du document, sous réserve des règles impératives applicables.

Signatures :
Éditeur : ____________________    Client : ____________________
Nom / qualité : ______________    Nom / qualité : ______________
Date : _______________________    Date : _______________________
"""

PRIVACY = f"""# POLITIQUE DE CONFIDENTIALITÉ ET DE PROTECTION DES DONNÉES SIGMA

Version : 1.0 — Date d'effet : 14/09/2026

{COMMON}

## 1. Rôle des parties
Pour les données scolaires saisies par l'établissement, celui-ci détermine les finalités et moyens du traitement dans son cadre de responsabilité. L'Éditeur agit selon le périmètre contractuel et les instructions documentées convenues avec l'établissement, sous réserve des obligations légales qui lui sont propres.

## 2. Données traitées
Selon les modules activés : identité des élèves, responsables, scolarité, évaluations, assiduité, discipline, facturation, paiements, communications, comptes utilisateurs, journaux techniques, appareils de synchronisation et documents générés.

## 3. Finalités
Gestion administrative et pédagogique, suivi des élèves, communication école-famille, facturation, production de documents, sécurité, synchronisation hors ligne, support, amélioration de la fiabilité et prévention des incidents.

## 4. Minimisation et accès
Les accès sont accordés selon les rôles et permissions. Les données ne doivent être collectées que pour des finalités déterminées, explicites et légitimes. Les fonctions d'export et de communication doivent être utilisées conformément aux autorisations de l'établissement.

## 5. Sécurité
SIGMA met en œuvre des contrôles d'accès, journalisation, séparation des établissements, sauvegardes, chiffrement lorsque prévu par l'infrastructure, et mécanismes de synchronisation idempotents. Aucun système ne peut garantir un risque nul.

## 6. Conservation
Les durées sont déterminées par les obligations légales, les besoins scolaires légitimes et les instructions contractuelles. [DÉCRIRE ICI LE CALENDRIER DE CONSERVATION FINAL PAR CATÉGORIE].

## 7. Sous-traitants et services tiers
SMS, WhatsApp, paiement Mobile Money, hébergement, e-mail ou autres services peuvent être fournis par des prestataires tiers lorsque les modules correspondants sont activés. La liste des prestataires, leurs rôles et leurs zones de traitement doivent être maintenus dans le registre des sous-traitants SIGMA.

## 8. Transferts et hébergement
Toute localisation ou tout transfert de données hors du périmètre convenu doit être documenté et soumis aux exigences applicables. [COMPLÉTER L'ARCHITECTURE D'HÉBERGEMENT ET LES GARANTIES DE TRANSFERT].

## 9. Droits des personnes
Les demandes relatives aux données doivent être traitées selon les droits et procédures applicables. L'établissement doit disposer d'un canal permettant aux personnes concernées de faire valoir leurs droits lorsque la loi le prévoit.

## 10. Incidents
Tout incident de sécurité susceptible d'affecter les données doit être enregistré, évalué, contenu et, lorsque requis, notifié aux personnes ou autorités compétentes selon les procédures applicables.

## 11. Contact
Responsable / point de contact données : [NOM OU SERVICE], [EMAIL], [TÉLÉPHONE], [ADRESSE].

Cette politique doit être adaptée à l'organisation réelle, aux sous-traitants et aux procédures de l'Éditeur et de chaque établissement.
"""

AUTH = f"""# AUTORISATION DE TRAITEMENT ET D'UTILISATION DE SIGMA PAR L'ÉTABLISSEMENT

Version : 1.0 — Date d'effet : 14/09/2026

{COMMON}

Je soussigné(e), [NOM], agissant en qualité de [FONCTION], pour [ÉTABLISSEMENT], autorise l'utilisation de SIGMA dans le périmètre souscrit et confirme que l'établissement dispose des habilitations nécessaires pour saisir, consulter, exporter et administrer les données confiées à la plateforme.

## 1. Finalités autorisées
- administration de l'établissement ;
- gestion des élèves et responsables ;
- gestion pédagogique et évaluations ;
- assiduité et discipline ;
- facturation et paiements ;
- communication avec les familles ;
- production de bulletins, cartes et documents ;
- sauvegarde, sécurité et synchronisation hors ligne ;
- support technique et maintenance.

## 2. Catégories de données
Données d'identification, scolarité, résultats, assiduité, discipline, informations financières, coordonnées de responsables, communications, comptes et journaux techniques, dans la limite des modules activés et des finalités autorisées.

## 3. Autorité du signataire
Le signataire confirme être habilité à engager l'établissement pour ce périmètre. L'établissement reste responsable de la légitimité de la collecte et des instructions transmises à SIGMA.

## 4. Communications
L'établissement autorise l'activation des canaux sélectionnés au contrat (notification SIGMA, portail, WhatsApp, SMS, e-mail), sous réserve des consentements, préférences et exigences applicables aux destinataires.

## 5. Révocation / modification
Toute modification substantielle du périmètre doit être communiquée par écrit ou via le mécanisme contractuel prévu. Une révocation peut affecter les fonctions concernées sans effacer les données dont la conservation demeure légalement ou contractuellement nécessaire.

## 6. Preuve
L'acceptation électronique peut être enregistrée avec la version du document, son empreinte cryptographique, la date/heure et les informations techniques disponibles.

Établissement : ____________________
Représentant : _____________________
Qualité : __________________________
Date : _____________________________
Signature / acceptation électronique : ____________________
"""

LEGAL_DOCUMENTS = [
    {'code':'SIGMA-LICENCE','version':'1.0','document_type':'license','title':'Contrat de licence et d’abonnement SIGMA','content':LICENSE,'effective_on':date(2026,9,14),'is_active':True,'is_required':True},
    {'code':'SIGMA-PRIVACY','version':'1.0','document_type':'privacy','title':'Politique de confidentialité et de protection des données SIGMA','content':PRIVACY,'effective_on':date(2026,9,14),'is_active':True,'is_required':True},
    {'code':'SIGMA-AUTHORIZATION','version':'1.0','document_type':'authorization','title':'Autorisation de traitement et d’utilisation de SIGMA','content':AUTH,'effective_on':date(2026,9,14),'is_active':True,'is_required':True},
]
