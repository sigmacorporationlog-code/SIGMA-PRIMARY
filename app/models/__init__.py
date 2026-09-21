"""
Importe tous les modèles pour que Base.metadata les connaisse
(nécessaire pour Alembic autogenerate et Base.metadata.create_all).
"""
from app.models.organization import Organization, School, Campus, AcademicYear, AcademicPeriod
from app.models.security import User, Post, Permission, PostPermission, UserPost, Delegation, AuditLog
from app.models.students import Level, Stream, SchoolClass, Guardian, Student, StudentGuardian, ClassMembership
from app.models.evaluation import (
    EvaluationFramework, EvaluationDomain, EvaluationCompetency, EvaluationCriterion,
    RatingScale, AppreciationRule, EvaluationActivity, EvaluationResult,
)
from app.models.academic import (
    Subject,
    TeacherAssignment,
    Assessment,
    Grade,
    GradeAudit,
    ReportCard,
    HonorBoardRule,
    HonorBoardEntry,
)
from app.models.attendance import AttendanceRecord, DisciplinaryRecord
from app.models.finance import FeeStructure, Invoice, Payment, Receipt, Expense, CashRegisterClosure
from app.models.finance_v3 import MobileMoneyConfiguration, PaymentTransaction, FinanceReminder
from app.models.documents import CardTemplate, IdCard
from app.models.communication import SmsMessage
from app.models.sync import SyncDevice, SyncOperation, SyncEntityVersion, SyncEntityIdentity
from app.models.notifications import Notification, PushSubscription, CommunicationPreference

__all__ = [
    "Organization", "School", "Campus", "AcademicYear", "AcademicPeriod",
    "User", "Post", "Permission", "PostPermission", "UserPost", "Delegation", "AuditLog",
    "Level", "Stream", "SchoolClass", "Guardian", "Student", "StudentGuardian", "ClassMembership",
    "Subject", "TeacherAssignment", "Assessment", "Grade", "GradeAudit", "ReportCard",
    "HonorBoardRule", "HonorBoardEntry",
    "EvaluationFramework", "EvaluationDomain", "EvaluationCompetency", "EvaluationCriterion",
    "RatingScale", "AppreciationRule", "EvaluationActivity", "EvaluationResult",
    "AttendanceRecord", "DisciplinaryRecord",
    "FeeStructure", "Invoice", "Payment", "Receipt", "Expense", "CashRegisterClosure",
    "MobileMoneyConfiguration", "PaymentTransaction", "FinanceReminder",
    "CardTemplate", "IdCard",
    "SmsMessage",
    "SyncDevice", "SyncOperation", "SyncEntityVersion", "SyncEntityIdentity",
    "Notification", "PushSubscription", "CommunicationPreference",
    "SchoolSubscription", "CloudEvent",
    "MessageTemplate", "MessageCampaign", "MessageRecipient", "MessageDelivery",
    "MessageConversation", "WhatsAppConfiguration",
    "CloudPlan", "CloudUsageSnapshot",
    "LegalDocument", "LegalAcceptance", "DataProcessingAuthorization",
    "SubscriptionInvoice", "SubscriptionPayment",
    "AIInteraction", "AIActionProposal", "AIKnowledgeDocument", "AIKnowledgeChunk",
    "PaymentGatewayEvent",
]
from app.models.communication_v3 import MessageTemplate, MessageCampaign, MessageRecipient, MessageDelivery, MessageConversation, WhatsAppConfiguration
from app.models.document_jobs import DocumentJob
from app.models.cloud import SchoolSubscription, CloudEvent, CloudPlan, CloudUsageSnapshot
from app.models.legal import LegalDocument, LegalAcceptance, DataProcessingAuthorization
from app.models.billing_v4 import SubscriptionInvoice, SubscriptionPayment
from app.models.ai import AIInteraction
from app.models.ai_actions import AIActionProposal

from app.models.ai_knowledge import AIKnowledgeDocument, AIKnowledgeChunk

from app.models.onboarding import SchoolOnboarding
from app.models.operations_v4 import PlatformIncident, PlatformMetricSnapshot
from app.models.payment_gateway import PaymentGatewayEvent

from app.models.fleet_v4 import FleetInstallation, FleetRollout
from app.models.backup_cloud import CloudBackupDestination
