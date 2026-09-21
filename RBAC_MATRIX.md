# RBAC_MATRIX.md

Source of truth: `app/services/permission_catalog.py`; route references and role profiles audited from current workspace.

## ROLE `direction`

| Module | Action | Permission | Label |
|---|---|---|---|
| academic | READ | `academic.assessments.view` | Consulter les évaluations |
| academic | READ | `academic.grades.view` | Consulter les notes |
| academic | EXPORT | `academic.report_cards.generate` | Générer des bulletins |
| academic | ADMIN | `academic.report_cards.publish` | Publier des bulletins |
| administration | ADMIN | `administration.ai.execute` | Exécuter des actions IA |
| administration | READ | `administration.ai.use` | Utiliser l'IA |
| administration | READ | `administration.audit.view` | Consulter le journal d'audit |
| administration | CREATE | `administration.backup.create` | Créer une sauvegarde |
| administration | READ | `administration.backup.view` | Consulter les sauvegardes |
| administration | CREATE | `administration.classes.create` | Créer des classes |
| administration | ADMIN | `administration.operations.execute` | Exécuter les opérations de maintenance |
| administration | READ | `administration.operations.view` | Consulter la supervision |
| administration | CONFIGURE | `administration.permissions.modify` | Modifier des permissions |
| administration | READ | `administration.permissions.view` | Consulter le catalogue des permissions |
| administration | CREATE | `administration.posts.create` | Créer des postes |
| administration | READ | `administration.posts.view` | Consulter les postes |
| administration | CONFIGURE | `administration.settings.modify` | Modifier les paramètres |
| administration | READ | `administration.system.view` | Consulter la santé système |
| administration | CREATE | `administration.users.create` | Créer des utilisateurs |
| administration | UPDATE | `administration.users.modify` | Modifier des utilisateurs |
| administration | READ | `administration.users.view` | Consulter les utilisateurs |
| cards | CONFIGURE | `cards.templates.modify` | Modifier les modèles de carte |
| cards | READ | `cards.templates.view` | Consulter les modèles de carte |
| cards | READ | `cards.view` | Consulter les cartes |
| communication | CREATE | `communication.sms.send` | Envoyer des SMS via le boîtier |
| communication | READ | `communication.sms.view` | Consulter les journaux SMS |
| finance | READ | `finance.cash.view` | Consulter la caisse |
| finance | EXPORT | `finance.payments.export` | Exporter les données financières |
| finance | EXPORT | `finance.payments.print_receipt` | Imprimer un reçu |
| finance | READ | `finance.payments.view` | Consulter les paiements |
| students | DELETE | `students.archive` | Archiver un élève |
| students | CREATE | `students.create` | Créer un élève |
| students | EXPORT | `students.export` | Exporter les élèves |
| students | UPDATE | `students.modify` | Modifier un élève |
| students | UPDATE | `students.transfer` | Transférer / inscrire un élève |
| students | READ | `students.view` | Consulter les élèves |

## ROLE `administration`

| Module | Action | Permission | Label |
|---|---|---|---|
| administration | READ | `administration.audit.view` | Consulter le journal d'audit |
| administration | CREATE | `administration.backup.create` | Créer une sauvegarde |
| administration | READ | `administration.backup.view` | Consulter les sauvegardes |
| administration | CREATE | `administration.classes.create` | Créer des classes |
| administration | ADMIN | `administration.operations.execute` | Exécuter les opérations de maintenance |
| administration | READ | `administration.operations.view` | Consulter la supervision |
| administration | READ | `administration.permissions.view` | Consulter le catalogue des permissions |
| administration | READ | `administration.posts.view` | Consulter les postes |
| administration | CONFIGURE | `administration.settings.modify` | Modifier les paramètres |
| administration | READ | `administration.system.view` | Consulter la santé système |
| administration | CREATE | `administration.users.create` | Créer des utilisateurs |
| administration | UPDATE | `administration.users.modify` | Modifier des utilisateurs |
| administration | READ | `administration.users.view` | Consulter les utilisateurs |
| cards | CONFIGURE | `cards.templates.modify` | Modifier les modèles de carte |
| cards | READ | `cards.templates.view` | Consulter les modèles de carte |
| cards | READ | `cards.view` | Consulter les cartes |
| communication | CREATE | `communication.sms.send` | Envoyer des SMS via le boîtier |
| communication | READ | `communication.sms.view` | Consulter les journaux SMS |
| students | DELETE | `students.archive` | Archiver un élève |
| students | CREATE | `students.create` | Créer un élève |
| students | EXPORT | `students.export` | Exporter les élèves |
| students | IMPORT | `students.import` | Importer des élèves |
| students | UPDATE | `students.modify` | Modifier un élève |
| students | UPDATE | `students.transfer` | Transférer / inscrire un élève |
| students | READ | `students.view` | Consulter les élèves |

## ROLE `enseignant`

| Module | Action | Permission | Label |
|---|---|---|---|
| academic | CREATE | `academic.assessments.create` | Créer une évaluation |
| academic | UPDATE | `academic.assessments.modify` | Modifier une évaluation |
| academic | READ | `academic.assessments.view` | Consulter les évaluations |
| academic | UPDATE | `academic.grades.enter` | Saisir des notes |
| academic | READ | `academic.grades.view` | Consulter les notes |
| evaluation | UPDATE | `evaluation.results.enter` | Saisir les résultats pédagogiques |
| evaluation | READ | `evaluation.results.view` | Consulter les résultats pédagogiques |
| students | READ | `students.view` | Consulter les élèves |

## ROLE `comptabilite`

| Module | Action | Permission | Label |
|---|---|---|---|
| finance | ADMIN | `finance.cash.close` | Effectuer une clôture de caisse |
| finance | READ | `finance.cash.view` | Consulter la caisse |
| finance | EXPORT | `finance.payments.export` | Exporter les données financières |
| finance | UPDATE | `finance.payments.modify` | Modifier un paiement |
| finance | EXPORT | `finance.payments.print_receipt` | Imprimer un reçu |
| finance | CREATE | `finance.payments.record` | Enregistrer un paiement |
| finance | READ | `finance.payments.view` | Consulter les paiements |

## ROLE `vie_scolaire`

| Module | Action | Permission | Label |
|---|---|---|---|
| cards | READ | `cards.templates.view` | Consulter les modèles de carte |
| cards | READ | `cards.view` | Consulter les cartes |
| students | DELETE | `students.archive` | Archiver un élève |
| students | EXPORT | `students.export` | Exporter les élèves |
| students | UPDATE | `students.modify` | Modifier un élève |
| students | UPDATE | `students.transfer` | Transférer / inscrire un élève |
| students | READ | `students.view` | Consulter les élèves |

## ROLE `lecture_seule`

| Module | Action | Permission | Label |
|---|---|---|---|
| academic | READ | `academic.assessments.view` | Consulter les évaluations |
| academic | READ | `academic.grades.view` | Consulter les notes |
| cards | READ | `cards.templates.view` | Consulter les modèles de carte |
| cards | READ | `cards.view` | Consulter les cartes |
| communication | READ | `communication.sms.view` | Consulter les journaux SMS |
| evaluation | READ | `evaluation.results.view` | Consulter les résultats pédagogiques |
| finance | EXPORT | `finance.payments.export` | Exporter les données financières |
| finance | READ | `finance.payments.view` | Consulter les paiements |
| students | EXPORT | `students.export` | Exporter les élèves |
| students | READ | `students.view` | Consulter les élèves |

## Route/service permission coverage

| Route/function | Permissions referenced |
|---|---|
| `app/api/academic.py::_teacher_academic_guard` | `academic.report_cards.publish`, `administration.settings.modify`, `administration.users.modify` |
| `app/api/academic.py::assign_teacher` | `administration.settings.modify` |
| `app/api/academic.py::create_assessment` | `academic.assessments.create`, `academic.grades.create` |
| `app/api/academic.py::create_subject` | `administration.settings.modify` |
| `app/api/academic.py::deactivate_subject` | `administration.settings.modify` |
| `app/api/academic.py::download_class_report_cards_pdf` | `academic.report_cards.generate` |
| `app/api/academic.py::download_report_card_pdf` | `academic.report_cards.generate` |
| `app/api/academic.py::generate_report_cards` | `academic.report_cards.generate` |
| `app/api/academic.py::get_class_ranking` | `academic.grades.view` |
| `app/api/academic.py::get_student_average` | `academic.grades.view` |
| `app/api/academic.py::list_assessment_grades` | `academic.grades.enter`, `academic.grades.view` |
| `app/api/academic.py::list_assessments` | `academic.assessments.view`, `academic.grades.enter`, `academic.grades.view`, `academic.report_cards.publish`, `administration.settings.modify`, `administration.users.modify` |
| `app/api/academic.py::list_class_report_cards` | `academic.report_cards.generate` |
| `app/api/academic.py::list_subjects` | `academic.assessments.view` |
| `app/api/academic.py::list_teacher_assignments` | `academic.assessments.view` |
| `app/api/academic.py::list_teachers` | `academic.assessments.view` |
| `app/api/academic.py::publish_report_card` | `academic.report_cards.publish` |
| `app/api/academic.py::restore_subject` | `administration.settings.modify` |
| `app/api/academic.py::transition_grades` | `academic.grades.lock`, `academic.grades.validate`, `academic.report_cards.publish` |
| `app/api/academic.py::update_subject` | `administration.settings.modify` |
| `app/api/academic.py::upsert_grades` | `academic.grades.enter` |
| `app/api/backup_cloud.py::add_cloud_destination` | `administration.backup.create` |
| `app/api/backup_cloud.py::delete_cloud_destination` | `administration.backup.create` |
| `app/api/backup_cloud.py::list_cloud_destinations` | `administration.backup.view` |
| `app/api/backup_cloud.py::test_cloud_destination` | `administration.backup.create` |
| `app/api/cards.py::bulk_issue_class_cards` | `cards.issue` |
| `app/api/cards.py::create_card_template` | `administration.settings.modify` |
| `app/api/cards.py::download_card_pdf` | `cards.view` |
| `app/api/cards.py::download_class_cards_pdf` | `cards.view` |
| `app/api/cards.py::edit_card_template` | `administration.settings.modify` |
| `app/api/cards.py::issue_card` | `cards.issue` |
| `app/api/cards.py::list_card_templates` | `cards.templates.view` |
| `app/api/cards.py::list_cards` | `cards.view` |
| `app/api/cards.py::print_card` | `cards.issue` |
| `app/api/cards.py::print_class_cards` | `cards.issue` |
| `app/api/cards.py::revoke_card` | `cards.issue` |
| `app/api/cards.py::update_card_lifecycle` | `cards.issue` |
| `app/api/communication.py::list_sms_logs` | `communication.sms.view` |
| `app/api/communication.py::retry_sms` | `communication.sms.send` |
| `app/api/communication.py::send_sms_to_class` | `communication.sms.send` |
| `app/api/communication.py::send_sms_to_guardian` | `communication.sms.send` |
| `app/api/communication.py::send_sms_to_phone` | `communication.sms.send` |
| `app/api/communication.py::send_sms_to_target` | `communication.sms.send` |
| `app/api/communication.py::send_sms_to_unpaid` | `communication.sms.send` |
| `app/api/communication.py::sms_provider_status` | `communication.sms.view` |
| `app/api/communication_v3.py::configure_whatsapp` | `administration.settings.modify` |
| `app/api/communication_v3.py::create_campaign` | `communication.sms.send` |
| `app/api/communication_v3.py::create_template` | `communication.sms.send` |
| `app/api/communication_v3.py::list_campaigns` | `communication.sms.view` |
| `app/api/communication_v3.py::list_deliveries` | `communication.sms.view` |
| `app/api/communication_v3.py::list_templates` | `communication.sms.view` |
| `app/api/communication_v3.py::send_message` | `communication.sms.send` |
| `app/api/evaluation.py::_check_activity_scope` | `academic.grades.enter`, `academic.grades.view`, `evaluation.results.enter`, `evaluation.results.view` |
| `app/api/evaluation.py::_teacher_assignment_guard` | `academic.report_cards.publish`, `administration.settings.modify`, `administration.users.modify` |
| `app/api/evaluation.py::activities` | `academic.grades.view`, `academic.report_cards.publish`, `administration.settings.modify`, `administration.users.modify`, `evaluation.results.view` |
| `app/api/evaluation.py::create_activity` | `academic.grades.enter`, `evaluation.results.enter` |
| `app/api/evaluation.py::create_appreciation_rule` | `evaluation.appreciations.modify` |
| `app/api/evaluation.py::create_competency` | `administration.settings.modify` |
| `app/api/evaluation.py::create_criterion` | `administration.settings.modify` |
| `app/api/evaluation.py::create_domain` | `administration.settings.modify` |
| `app/api/evaluation.py::create_framework` | `administration.settings.modify` |
| `app/api/evaluation.py::create_scale` | `administration.settings.modify` |
| `app/api/evaluation.py::finalize_class_period` | `evaluation.periods.close` |
| `app/api/evaluation.py::patch_competency` | `administration.settings.modify` |
| `app/api/evaluation.py::patch_criterion` | `administration.settings.modify` |
| `app/api/evaluation.py::patch_domain` | `administration.settings.modify` |
| `app/api/evaluation.py::patch_framework` | `administration.settings.modify` |
| `app/api/evaluation.py::patch_scale` | `administration.settings.modify` |
| `app/api/evaluation.py::publish_class_period` | `evaluation.periods.publish` |
| `app/api/evaluation.py::transition_evaluation_results` | `evaluation.results.lock`, `evaluation.results.validate` |
| `app/api/finance.py::cancel_payment` | `finance.payments.cancel` |
| `app/api/finance.py::create_fee_structure` | `administration.settings.modify` |
| `app/api/finance.py::create_invoice` | `finance.payments.record` |
| `app/api/finance.py::download_receipt_pdf` | `finance.payments.print_receipt` |
| `app/api/finance.py::finance_overview` | `finance.payments.view` |
| `app/api/finance.py::get_receipt` | `finance.payments.view` |
| `app/api/finance.py::list_student_invoices` | `finance.payments.view` |
| `app/api/finance.py::list_student_payments` | `finance.payments.view` |
| `app/api/finance.py::overdue_invoices` | `finance.payments.view` |
| `app/api/finance.py::queue_finance_reminder` | `finance.payments.record` |
| `app/api/finance.py::reconcile_mobile_money` | `finance.payments.record` |
| `app/api/finance.py::record_payment` | `finance.payments.record` |
| `app/api/finance.py::reprint_receipt` | `finance.payments.print_receipt` |
| `app/api/finance.py::save_mobile_money_config` | `administration.settings.modify` |
| `app/api/fleet.py::fleet_heartbeat` | `administration.operations.execute` |
| `app/api/fleet.py::overview` | `administration.operations.view` |
| `app/api/fleet.py::rollout` | `administration.operations.execute` |
| `app/api/fleet.py::rollout_evaluate` | `administration.operations.execute` |
| `app/api/honor_board.py::_honor_scope_context` | `academic.report_cards.publish`, `administration.settings.modify`, `administration.users.modify` |
| `app/api/honor_board.py::create_rule` | `administration.settings.modify` |
| `app/api/honor_board.py::deactivate_rule` | `administration.settings.modify` |
| `app/api/honor_board.py::entries` | `academic.grades.view` |
| `app/api/honor_board.py::export_csv` | `academic.report_cards.generate` |
| `app/api/honor_board.py::export_pdf` | `academic.report_cards.generate` |
| `app/api/honor_board.py::generate` | `academic.report_cards.generate` |
| `app/api/honor_board.py::history` | `academic.grades.view` |
| `app/api/honor_board.py::list_rules` | `academic.grades.view` |
| `app/api/honor_board.py::preview` | `academic.grades.view` |
| `app/api/honor_board.py::update_rule` | `administration.settings.modify` |
| `app/api/honor_board.py::validate_entry` | `academic.report_cards.publish` |
| `app/api/honor_board.py::validate_rule` | `academic.report_cards.publish` |
| `app/api/onboarding.py::run_bootstrap` | `administration.settings.modify` |
| `app/api/operations_v4.py::control` | `administration.operations.view` |
| `app/api/operations_v4.py::incident` | `administration.operations.execute` |
| `app/api/operations_v4.py::incidents` | `administration.operations.view` |
| `app/api/operations_v4.py::resolve` | `administration.operations.execute` |
| `app/api/operations_v4.py::snapshot` | `administration.operations.execute` |
| `app/api/organization.py::create_academic_period` | `administration.settings.modify` |
| `app/api/organization.py::create_academic_year` | `administration.settings.modify` |
| `app/api/organization.py::create_campus` | `administration.settings.modify` |
| `app/api/organization.py::create_school` | `administration.schools.create` |
| `app/api/organization.py::update_school_settings` | `administration.settings.modify` |
| `app/api/organization.py::upload_school_logo` | `administration.settings.modify` |
| `app/api/organization.py::upload_school_stamp` | `administration.settings.modify` |
| `app/api/performance.py::metrics` | `administration.operations.view` |
| `app/api/pilot.py::prepare` | `administration.operations.execute` |
| `app/api/pilot.py::readiness` | `administration.system.view` |
| `app/api/sla.py::alerts` | `administration.operations.view` |
| `app/api/sla.py::current` | `administration.operations.view` |
| `app/api/sla.py::reconcile` | `administration.operations.execute` |
| `app/api/students.py::change_student_status` | `students.modify` |
| `app/api/students.py::class_edit_context` | `students.view` |
| `app/api/students.py::create_class` | `administration.classes.create` |
| `app/api/students.py::create_enrollment` | `students.transfer` |
| `app/api/students.py::create_guardian` | `students.modify` |
| `app/api/students.py::create_level` | `administration.settings.modify` |
| `app/api/students.py::create_stream` | `administration.settings.modify` |
| `app/api/students.py::create_student` | `students.create` |
| `app/api/students.py::deactivate_class` | `administration.classes.create` |
| `app/api/students.py::deactivate_level` | `administration.settings.modify` |
| `app/api/students.py::deactivate_stream` | `administration.settings.modify` |
| `app/api/students.py::enrollment_certificate` | `students.view` |
| `app/api/students.py::export_students_excel` | `students.export` |
| `app/api/students.py::export_students_pdf` | `students.export` |
| `app/api/students.py::get_student` | `students.view` |
| `app/api/students.py::get_student_photo` | `students.view` |
| `app/api/students.py::import_students_excel` | `students.import` |
| `app/api/students.py::link_guardian` | `students.modify` |
| `app/api/students.py::list_class_students` | `students.view` |
| `app/api/students.py::list_classes` | `students.view` |
| `app/api/students.py::list_guardians` | `students.view` |
| `app/api/students.py::list_levels` | `students.view` |
| `app/api/students.py::list_streams` | `students.view` |
| `app/api/students.py::list_student_guardians` | `students.view` |
| `app/api/students.py::list_students` | `students.view` |
| `app/api/students.py::preview_matricule` | `students.view` |
| `app/api/students.py::remove_student_photo` | `students.modify` |
| `app/api/students.py::restore_class` | `administration.classes.create` |
| `app/api/students.py::restore_level` | `administration.settings.modify` |
| `app/api/students.py::restore_stream` | `administration.settings.modify` |
| `app/api/students.py::student_360` | `students.view` |
| `app/api/students.py::student_dossier_pdf` | `students.view` |
| `app/api/students.py::student_enrollment` | `students.view` |
| `app/api/students.py::student_profile` | `students.view` |
| `app/api/students.py::students_grid` | `students.view` |
| `app/api/students.py::transfer_enrollment` | `students.transfer` |
| `app/api/students.py::update_class` | `administration.classes.create` |
| `app/api/students.py::update_guardian` | `students.modify` |
| `app/api/students.py::update_level` | `administration.settings.modify` |
| `app/api/students.py::update_stream` | `administration.settings.modify` |
| `app/api/students.py::upload_student_photo` | `students.modify` |
| `app/api/students.py::withdraw_student` | `students.modify` |
| `app/api/sync.py::_is_admin` | `administration.settings.modify` |
| `app/api/sync.py::_sync_permission_allowed` | `academic.grades.enter`, `academic.grades.lock`, `academic.grades.modify`, `academic.grades.validate`, `academic.report_cards.publish`, `administration.settings.modify`, `students.create`, `students.modify` |
| `app/api/sync.py::devices` | `administration.settings.modify` |
| `app/api/system.py::backup` | `administration.backup.create` |
| `app/api/system.py::backups` | `administration.backup.view` |
| `app/api/system.py::backups_prune` | `administration.operations.execute` |
| `app/api/system.py::capacity_detail` | `administration.system.view` |
| `app/api/system.py::download_backup` | `administration.backup.view` |
| `app/api/system.py::health_detail` | `administration.system.view` |
| `app/api/system.py::operations_overview` | `administration.operations.view` |
| `app/api/system.py::release_validate` | `administration.operations.execute` |
| `app/api/system.py::restore_cancel` | `administration.restore.execute` |
| `app/api/system.py::restore_prepare` | `administration.restore.execute` |
| `app/api/system.py::restore_status` | `administration.restore.view` |
| `app/api/system.py::security_posture_detail` | `administration.system.view` |
| `app/api/system.py::status` | `administration.system.view` |
| `app/api/system.py::upgrade_cancel` | `administration.upgrade.execute` |
| `app/api/system.py::upgrade_prepare` | `administration.upgrade.execute` |
| `app/api/system.py::upgrade_status` | `administration.upgrade.view` |
| `app/api/users.py::admin_reset_password` | `administration.users.modify` |
| `app/api/users.py::assign_permission_to_post` | `administration.permissions.modify` |
| `app/api/users.py::assign_permissions_to_post_bulk` | `administration.permissions.modify` |
| `app/api/users.py::assign_rbac_profile` | `administration.users.modify` |
| `app/api/users.py::assign_user_to_post` | `administration.users.modify` |
| `app/api/users.py::create_delegation` | `administration.permissions.modify` |
| `app/api/users.py::create_post` | `administration.posts.create` |
| `app/api/users.py::create_user` | `administration.users.create` |
| `app/api/users.py::get_user` | `administration.users.view` |
| `app/api/users.py::list_audit_logs` | `administration.audit.view` |
| `app/api/users.py::list_permissions` | `administration.permissions.view` |
| `app/api/users.py::list_post_permissions` | `administration.permissions.view` |
| `app/api/users.py::list_posts` | `administration.posts.view` |
| `app/api/users.py::list_user_posts` | `administration.users.view` |
| `app/api/users.py::list_users` | `administration.users.view` |
| `app/api/users.py::rbac_profiles` | `administration.permissions.view` |
| `app/api/users.py::remove_post_permission` | `administration.permissions.modify` |

## Findings
- Catalog permissions: **63**
- Roles: **6**
- Route/service functions with explicit permission references: **198**
- Referenced codes missing from catalog: **none**
