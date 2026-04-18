"""
Data models and schemas for ClaimFast insurance claims system.
Defines Pydantic models for API validation and inter-agent communication.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class ClaimType(str, Enum):
    """Insurance claim types supported by ClaimFast"""
    MOTOR = "motor"
    HEALTH = "health"
    PROPERTY = "property"


class DecisionStatus(str, Enum):
    """Claim decision outcomes"""
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class SeverityLevel(str, Enum):
    """Damage severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# INPUT SCHEMAS
# ============================================================================

class UserDetails(BaseModel):
    """User/claimant information"""
    name: str = Field(..., description="Full name of claimant")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    policy_id: str = Field(..., description="Insurance policy ID")


class ClaimSubmission(BaseModel):
    """Initial claim submission from user"""
    user_data: UserDetails
    claim_type: ClaimType
    incident_description: str = Field(..., description="Description of incident")
    incident_date: datetime
    incident_location: Optional[str] = None
    media_links: List[str] = Field(default_factory=list, description="URLs to images/videos")
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# AGENT OUTPUT SCHEMAS
# ============================================================================

class IntakeAgentOutput(BaseModel):
    """Output from FNOL Intake Agent"""
    claim_id: str
    claim_type: ClaimType
    user_data: UserDetails
    incident_summary: str
    media_links: List[str]
    status: str = "validated"
    validation_errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class DamageAssessmentOutput(BaseModel):
    """Output from Damage Assessment Agent (Vision)"""
    claim_id: str
    damage_type: str = Field(..., description="Type of damage detected")
    severity_score: int = Field(..., ge=0, le=100, description="Severity 0-100")
    severity_level: SeverityLevel
    affected_components: List[str] = Field(..., description="Affected parts/areas")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence 0-1")
    fraud_flag_visual: bool = Field(..., description="Visual fraud indicators")
    visual_details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class PolicyRule(BaseModel):
    """Individual policy rule"""
    rule_id: str
    description: str
    conditions: Dict[str, Any]
    action: str


class PolicyAgentOutput(BaseModel):
    """Output from Policy Understanding Agent"""
    claim_id: str
    coverage_valid: bool
    max_claim_amount: float
    deductible: float
    policy_rules: List[PolicyRule] = Field(default_factory=list)
    exclusions_triggered: List[str] = Field(default_factory=list)
    policy_details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class FraudDetectionOutput(BaseModel):
    """Output from Fraud Detection Agent"""
    claim_id: str
    fraud_risk_score: int = Field(..., ge=0, le=100)
    fraud_flags: List[str] = Field(default_factory=list)
    fraud_indicators: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = Field(..., description="approve/review/reject")
    timestamp: datetime = Field(default_factory=datetime.now)


class DecisionOutput(BaseModel):
    """Output from Decision Agent"""
    claim_id: str
    final_decision: DecisionStatus
    payout_amount: float
    reasoning: str
    confidence_score: float = Field(..., ge=0, le=1)
    decision_factors: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AuditLogEntry(BaseModel):
    """Individual audit log entry"""
    agent: str
    action: str
    timestamp: datetime
    details: Dict[str, Any]


class ExplainabilityOutput(BaseModel):
    """Output from Explainability & Audit Agent"""
    claim_id: str
    explanation_text: str
    audit_log: List[AuditLogEntry]
    policy_clauses_used: List[str]
    damage_findings: Dict[str, Any]
    fraud_signals: List[str]
    compliance_status: str = "IRDAI-ready"
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# PIPELINE ORCHESTRATION SCHEMA
# ============================================================================

class ClaimProcessingContext(BaseModel):
    """Context passed through the entire claim processing pipeline"""
    claim_id: str
    original_submission: ClaimSubmission
    intake_output: Optional[IntakeAgentOutput] = None
    damage_assessment_output: Optional[DamageAssessmentOutput] = None
    policy_output: Optional[PolicyAgentOutput] = None
    fraud_detection_output: Optional[FraudDetectionOutput] = None
    decision_output: Optional[DecisionOutput] = None
    explainability_output: Optional[ExplainabilityOutput] = None
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
    processing_start_time: datetime = Field(default_factory=datetime.now)
    processing_end_time: Optional[datetime] = None


class ClaimStatusResponse(BaseModel):
    """Response for claim status queries"""
    claim_id: str
    status: str
    current_stage: str
    progress_percentage: int
    latest_decision: Optional[DecisionStatus] = None
    payout_amount: Optional[float] = None
    last_updated: datetime


class ClaimSubmissionResponse(BaseModel):
    """Response to initial claim submission"""
    claim_id: str
    status: str
    message: str
    estimated_processing_time: str = "Less than 60 seconds"
    timestamp: datetime = Field(default_factory=datetime.now)
