"""
FNOL Intake Agent - First stage of claim processing.
Validates and standardizes claim input data.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

from models.schemas import (
    ClaimSubmission, IntakeAgentOutput, UserDetails, ClaimType, AuditLogEntry
)

logger = logging.getLogger(__name__)


class FNOLIntakeAgent:
    """
    Agent responsible for accepting and validating initial claim submissions.
    
    Responsibilities:
    - Validate completeness of inputs
    - Standardize input format into JSON
    - Detect missing/invalid data
    - Request re-upload if needed
    """
    
    def __init__(self):
        self.agent_name = "FNOL_Intake_Agent"
        self.required_fields = {
            "motor": ["name", "policy_id", "incident_description", "incident_date"],
            "health": ["name", "policy_id", "incident_description", "incident_date"],
            "property": ["name", "policy_id", "incident_description", "incident_date"],
        }
    
    @staticmethod
    def validate_user_details(user_data: dict) -> Dict[str, Any]:
        """Validate user details completeness and format"""
        required_fields = ["name", "email", "phone", "policy_id"]
        missing_fields = [field for field in required_fields if field not in user_data]
        
        if missing_fields:
            return {
                "valid": False,
                "errors": [f"Missing field: {field}" for field in missing_fields]
            }
        
        # Basic email validation
        if "@" not in user_data.get("email", ""):
            return {
                "valid": False,
                "errors": ["Invalid email format"]
            }
        
        # Basic phone validation (assuming Indian format)
        phone = user_data.get("phone", "").replace(" ", "").replace("-", "")
        if not phone.isdigit() or len(phone) < 10:
            return {
                "valid": False,
                "errors": ["Invalid phone number (should be 10+ digits)"]
            }
        
        return {"valid": True, "errors": []}
    
    @staticmethod
    def validate_claim_type(claim_type: str) -> Dict[str, Any]:
        """Validate claim type is supported"""
        valid_types = ["motor", "health", "property"]
        if claim_type.lower() not in valid_types:
            return {
                "valid": False,
                "errors": [f"Invalid claim type. Supported: {', '.join(valid_types)}"]
            }
        return {"valid": True, "errors": []}
    
    @staticmethod
    def validate_media(media_links: List[str]) -> Dict[str, Any]:
        """Validate media links"""
        if not media_links:
            return {
                "valid": False,
                "errors": ["At least one media link (image/video) required"]
            }
        
        supported_formats = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"]
        errors = []
        
        for link in media_links:
            if not any(link.lower().endswith(fmt) for fmt in supported_formats):
                errors.append(f"Unsupported media format: {link}")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        return {"valid": True, "errors": []}
    
    def process_claim(self, submission: ClaimSubmission) -> IntakeAgentOutput:
        """
        Main processing method for claim intake.
        
        Args:
            submission: ClaimSubmission object with claim data
            
        Returns:
            IntakeAgentOutput with validated claim data
        """
        claim_id = f"CLM_{uuid.uuid4().hex[:12].upper()}"
        validation_errors = []
        
        logger.info(f"Processing claim intake for {claim_id}")
        
        # Validate user details
        user_validation = self.validate_user_details(submission.user_data.dict())
        if not user_validation["valid"]:
            validation_errors.extend(user_validation["errors"])
        
        # Validate claim type
        claim_type_validation = self.validate_claim_type(submission.claim_type)
        if not claim_type_validation["valid"]:
            validation_errors.extend(claim_type_validation["errors"])
        
        # Validate media
        media_validation = self.validate_media(submission.media_links)
        if not media_validation["valid"]:
            validation_errors.extend(media_validation["errors"])
        
        # Validate incident description
        if not submission.incident_description or len(submission.incident_description) < 10:
            validation_errors.append("Incident description must be at least 10 characters")
        
        # Validate incident date is not in future.
        # Normalize both values to timezone-aware UTC to avoid aware/naive comparison errors.
        incident_date = submission.incident_date
        if incident_date.tzinfo is None:
            incident_date_utc = incident_date.replace(tzinfo=timezone.utc)
        else:
            incident_date_utc = incident_date.astimezone(timezone.utc)

        if incident_date_utc > datetime.now(timezone.utc):
            validation_errors.append("Incident date cannot be in the future")
        
        # Create summary
        incident_summary = self._create_summary(submission)
        
        # Determine status based on validation
        status = "validated" if not validation_errors else "validation_failed"
        
        logger.info(f"Intake validation for {claim_id}: {status}")
        
        output = IntakeAgentOutput(
            claim_id=claim_id,
            claim_type=submission.claim_type,
            user_data=submission.user_data,
            incident_summary=incident_summary,
            media_links=submission.media_links,
            status=status,
            validation_errors=validation_errors,
            timestamp=datetime.now()
        )
        
        return output
    
    def _create_summary(self, submission: ClaimSubmission) -> str:
        """Create a concise summary of the incident"""
        summary = (
            f"Claim Type: {submission.claim_type.value}. "
            f"Incident: {submission.incident_description[:200]}. "
            f"Date: {submission.incident_date.strftime('%Y-%m-%d %H:%M')}. "
        )
        
        if submission.incident_location:
            summary += f"Location: {submission.incident_location}. "
        
        summary += f"Media: {len(submission.media_links)} file(s) uploaded."
        
        return summary
    
    def get_audit_log(self, claim_id: str) -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="claim_intake_validation",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "stage": "FNOL Intake"
            }
        )


# Initialize singleton instance
intake_agent = FNOLIntakeAgent()


def process_intake(submission: ClaimSubmission) -> IntakeAgentOutput:
    """
    Public function to process claim intake.
    
    Args:
        submission: ClaimSubmission object
        
    Returns:
        IntakeAgentOutput with validation results
    """
    return intake_agent.process_claim(submission)
