"""Source de vérité du catalogue RBAC SIGMA.

Le catalogue est volontairement indépendant de SQLAlchemy afin d'être réutilisé
par le seed, les migrations, les profils de postes et les rapports d'audit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    module: str
    action: str
    label: str
    description: str = ""


PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec("students.view", "students", "READ", "Consulter les élèves"),
    PermissionSpec("students.create", "students", "CREATE", "Créer un élève"),
    PermissionSpec("students.modify", "students", "UPDATE", "Modifier un élève"),
    PermissionSpec("students.archive", "students", "DELETE", "Archiver un élève"),
    PermissionSpec("students.transfer", "students", "UPDATE", "Transférer / inscrire un élève"),
    PermissionSpec("students.delete", "students", "DELETE", "Supprimer un élève"),
    PermissionSpec("students.import", "students", "IMPORT", "Importer des élèves"),
    PermissionSpec("students.export", "students", "EXPORT", "Exporter les élèves"),

    PermissionSpec("academic.grades.view", "academic", "READ", "Consulter les notes"),
    PermissionSpec("academic.grades.create", "academic", "CREATE", "Créer une évaluation historique"),
    PermissionSpec("academic.grades.enter", "academic", "UPDATE", "Saisir des notes"),
    PermissionSpec("academic.grades.modify", "academic", "UPDATE", "Modifier des notes"),
    PermissionSpec("academic.grades.validate", "academic", "UPDATE", "Valider / faire progresser des notes"),
    PermissionSpec("academic.grades.lock", "academic", "UPDATE", "Verrouiller des notes"),
    PermissionSpec("academic.assessments.view", "academic", "READ", "Consulter les évaluations"),
    PermissionSpec("academic.assessments.create", "academic", "CREATE", "Créer une évaluation"),
    PermissionSpec("academic.assessments.modify", "academic", "UPDATE", "Modifier une évaluation"),
    PermissionSpec("academic.assessments.delete", "academic", "DELETE", "Supprimer une évaluation"),
    PermissionSpec("evaluation.results.view", "evaluation", "READ", "Consulter les résultats pédagogiques"),
    PermissionSpec("evaluation.results.enter", "evaluation", "UPDATE", "Saisir les résultats pédagogiques"),
    PermissionSpec("evaluation.results.validate", "evaluation", "UPDATE", "Valider les résultats pédagogiques"),
    PermissionSpec("evaluation.results.lock", "evaluation", "UPDATE", "Verrouiller les résultats pédagogiques"),
    PermissionSpec("evaluation.appreciations.modify", "evaluation", "CONFIGURE", "Configurer les appréciations automatiques"),
    PermissionSpec("academic.report_cards.generate", "academic", "EXPORT", "Générer des bulletins"),
    PermissionSpec("academic.report_cards.publish", "academic", "ADMIN", "Publier des bulletins"),
    PermissionSpec("evaluation.periods.close", "evaluation", "ADMIN", "Clôturer une période pédagogique"),
    PermissionSpec("evaluation.periods.publish", "evaluation", "ADMIN", "Publier les bulletins d'une période"),

    PermissionSpec("finance.payments.view", "finance", "READ", "Consulter les paiements"),
    PermissionSpec("finance.payments.record", "finance", "CREATE", "Enregistrer un paiement"),
    PermissionSpec("finance.payments.modify", "finance", "UPDATE", "Modifier un paiement"),
    PermissionSpec("finance.payments.cancel", "finance", "DELETE", "Annuler un paiement"),
    PermissionSpec("finance.payments.print_receipt", "finance", "EXPORT", "Imprimer un reçu"),
    PermissionSpec("finance.payments.export", "finance", "EXPORT", "Exporter les données financières"),
    PermissionSpec("finance.cash.view", "finance", "READ", "Consulter la caisse"),
    PermissionSpec("finance.cash.close", "finance", "ADMIN", "Effectuer une clôture de caisse"),

    PermissionSpec("administration.schools.create", "administration", "CREATE", "Créer un établissement"),
    PermissionSpec("administration.users.view", "administration", "READ", "Consulter les utilisateurs"),
    PermissionSpec("administration.users.create", "administration", "CREATE", "Créer des utilisateurs"),
    PermissionSpec("administration.users.modify", "administration", "UPDATE", "Modifier des utilisateurs"),
    PermissionSpec("administration.posts.view", "administration", "READ", "Consulter les postes"),
    PermissionSpec("administration.posts.create", "administration", "CREATE", "Créer des postes"),
    PermissionSpec("administration.permissions.view", "administration", "READ", "Consulter le catalogue des permissions"),
    PermissionSpec("administration.permissions.modify", "administration", "CONFIGURE", "Modifier des permissions"),
    PermissionSpec("administration.audit.view", "administration", "READ", "Consulter le journal d'audit"),
    PermissionSpec("administration.settings.modify", "administration", "CONFIGURE", "Modifier les paramètres"),
    PermissionSpec("administration.classes.create", "administration", "CREATE", "Créer des classes"),
    PermissionSpec("administration.backup.view", "administration", "READ", "Consulter les sauvegardes"),
    PermissionSpec("administration.backup.create", "administration", "CREATE", "Créer une sauvegarde"),
    PermissionSpec("administration.restore.view", "administration", "READ", "Consulter l'état de restauration"),
    PermissionSpec("administration.restore.execute", "administration", "ADMIN", "Exécuter une restauration"),
    PermissionSpec("administration.upgrade.view", "administration", "READ", "Consulter l'état des mises à niveau"),
    PermissionSpec("administration.upgrade.execute", "administration", "ADMIN", "Exécuter une mise à niveau"),
    PermissionSpec("administration.system.view", "administration", "READ", "Consulter la santé système"),
    PermissionSpec("administration.operations.view", "administration", "READ", "Consulter la supervision"),
    PermissionSpec("administration.operations.execute", "administration", "ADMIN", "Exécuter les opérations de maintenance"),
    PermissionSpec("administration.ai.use", "administration", "READ", "Utiliser l'IA"),
    PermissionSpec("administration.ai.execute", "administration", "ADMIN", "Exécuter des actions IA"),

    PermissionSpec("cards.view", "cards", "READ", "Consulter les cartes"),
    PermissionSpec("cards.issue", "cards", "CREATE", "Émettre / révoquer des cartes d'accès"),
    PermissionSpec("cards.templates.view", "cards", "READ", "Consulter les modèles de carte"),
    PermissionSpec("cards.templates.modify", "cards", "CONFIGURE", "Modifier les modèles de carte"),

    PermissionSpec("communication.sms.view", "communication", "READ", "Consulter les journaux SMS"),
    PermissionSpec("communication.sms.send", "communication", "CREATE", "Envoyer des SMS via le boîtier"),
)

PERMISSION_BY_CODE = {item.code: item for item in PERMISSIONS}
