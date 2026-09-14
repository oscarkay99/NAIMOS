import enum


class RoleName(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    NATIONAL_ADMIN = "NATIONAL_ADMIN"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    FIELD_SUPERVISOR = "FIELD_SUPERVISOR"
    FIELD_OFFICER = "FIELD_OFFICER"
    INTELLIGENCE_ANALYST = "INTELLIGENCE_ANALYST"
    ENVIRONMENTAL_ANALYST = "ENVIRONMENTAL_ANALYST"
    PRO = "PRO"
    REPORT_VIEWER = "REPORT_VIEWER"
    AUDITOR = "AUDITOR"


class IncidentStatus(str, enum.Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    FIELD_VERIFICATION_REQUIRED = "FIELD_VERIFICATION_REQUIRED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RiskCategory(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @staticmethod
    def from_score(score: int) -> "RiskCategory":
        if score <= 20:
            return RiskCategory.LOW
        if score <= 40:
            return RiskCategory.MODERATE
        if score <= 60:
            return RiskCategory.ELEVATED
        if score <= 80:
            return RiskCategory.HIGH
        return RiskCategory.CRITICAL


class DataClassification(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class IncidentType(str, enum.Enum):
    SUSPECTED_ILLEGAL_MINING = "SUSPECTED_ILLEGAL_MINING"
    LAND_DISTURBANCE = "LAND_DISTURBANCE"
    WATER_POLLUTION = "WATER_POLLUTION"
    VEGETATION_LOSS = "VEGETATION_LOSS"
    UNAUTHORIZED_EQUIPMENT = "UNAUTHORIZED_EQUIPMENT"
    OTHER = "OTHER"


class SourceType(str, enum.Enum):
    FIELD_REPORT = "FIELD_REPORT"
    PUBLIC_REPORT = "PUBLIC_REPORT"
    AI_DETECTION = "AI_DETECTION"
    ANALYST_ENTRY = "ANALYST_ENTRY"


class Priority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationStage(str, enum.Enum):
    REPORT = "REPORT"
    AI_TRIAGE = "AI_TRIAGE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FIELD_VERIFICATION = "FIELD_VERIFICATION"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    INVESTIGATION = "INVESTIGATION"
    RESOLUTION = "RESOLUTION"
    CLOSED = "CLOSED"


class EvidenceFileType(str, enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"


class DetectionType(str, enum.Enum):
    VEGETATION_LOSS = "VEGETATION_LOSS"
    EXPOSED_SOIL = "EXPOSED_SOIL"
    EXCAVATION = "EXCAVATION"
    NEW_ROAD = "NEW_ROAD"
    PIT_EXPANSION = "PIT_EXPANSION"
    WATER_SEDIMENTATION = "WATER_SEDIMENTATION"


class AIReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    USEFUL = "USEFUL"
    NOT_USEFUL = "NOT_USEFUL"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    PUSH = "PUSH"
