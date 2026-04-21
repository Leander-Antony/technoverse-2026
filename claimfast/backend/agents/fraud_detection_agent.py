"""
Fraud Detection Agent - Suspicious claim detection.
Cross-checks claim data against fraud indicators and patterns.
"""

import json
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
import logging
import hashlib
import importlib.util
from pathlib import Path
from urllib.parse import urlparse, unquote

from models.schemas import (
    FraudDetectionOutput, DamageAssessmentOutput, AuditLogEntry
)
from config.settings import config

logger = logging.getLogger(__name__)


class FraudDetectionAgent:
    """
    Agent responsible for detecting fraudulent claims.
    
    Responsibilities:
    - Cross-check claim history
    - Detect duplicate claims
    - Identify unusual severity vs description mismatch
    - Analyze metadata inconsistencies
    """
    
    def __init__(self):
        self.agent_name = "Fraud_Detection_Agent"
        self.use_mock_db = config.USE_MOCK_FRAUD_DB
        self.fake_image_detector = self._load_fake_image_detector()
        
        # Mock claim history database
        self.claim_history_db = {}
        self.fraud_patterns_db = self._initialize_fraud_patterns()
    
    def detect_fraud(self, claim_id: str, policy_id: str, user_email: str,
                    damage_assessment: DamageAssessmentOutput,
                    incident_description: str,
                    incident_date: datetime,
                    incident_location: str,
                    media_links: List[str] | None = None) -> FraudDetectionOutput:
        """
        Detect fraud indicators in claim.
        
        Args:
            claim_id: Unique claim identifier
            policy_id: Insurance policy ID
            user_email: Claimant email
            damage_assessment: Damage assessment from vision agent
            incident_description: Text description of incident
            incident_date: Date of incident
            incident_location: Location of incident
            
        Returns:
            FraudDetectionOutput with fraud risk score
        """
        logger.info(f"Starting fraud detection for claim {claim_id}")
        
        fraud_score = 0
        fraud_flags = []
        fraud_indicators = {}
        
        # 1. Check claim history
        history_risk, history_flags, history_details = self._check_claim_history(
            policy_id, user_email
        )
        fraud_score += history_risk
        fraud_flags.extend(history_flags)
        fraud_indicators["claim_history"] = history_details
        
        # 2. Check duplicate claims
        duplicate_risk, duplicate_flags, duplicate_details = self._check_duplicate_claims(
            policy_id, incident_date, incident_location
        )
        fraud_score += duplicate_risk
        fraud_flags.extend(duplicate_flags)
        fraud_indicators["duplicate_check"] = duplicate_details
        
        # 3. Analyze description vs damage mismatch
        mismatch_risk, mismatch_flags, mismatch_details = self._check_description_mismatch(
            incident_description, damage_assessment
        )
        fraud_score += mismatch_risk
        fraud_flags.extend(mismatch_flags)
        fraud_indicators["description_mismatch"] = mismatch_details
        
        # 4. Analyze metadata inconsistencies
        metadata_risk, metadata_flags, metadata_details = self._check_metadata_consistency(
            incident_date, incident_location, damage_assessment
        )
        fraud_score += metadata_risk
        fraud_flags.extend(metadata_flags)
        fraud_indicators["metadata"] = metadata_details
        
        # 5. Pattern matching against known fraud patterns
        pattern_risk, pattern_flags, pattern_details = self._check_fraud_patterns(
            claim_id, policy_id, damage_assessment, incident_description
        )
        fraud_score += pattern_risk
        fraud_flags.extend(pattern_flags)
        fraud_indicators["fraud_patterns"] = pattern_details

        # 6. Image authenticity analysis using fake_image.py heuristics
        image_risk, image_flags, image_details = self._check_image_authenticity(media_links or [])
        fraud_score += image_risk
        fraud_flags.extend(image_flags)
        fraud_indicators["image_authenticity"] = image_details
        logger.info(
            "Image authenticity for %s: analyzed=%s/%s, risk_delta=%s, detector_loaded=%s",
            claim_id,
            image_details.get("images_analyzed", 0),
            image_details.get("media_links_received", 0),
            image_risk,
            image_details.get("detector_loaded", False),
        )
        
        # Cap score at 100
        fraud_score = min(fraud_score, 100)
        
        # Determine recommended action
        recommended_action = self._determine_action(fraud_score)
        
        output = FraudDetectionOutput(
            claim_id=claim_id,
            fraud_risk_score=fraud_score,
            fraud_flags=list(set(fraud_flags)),  # Remove duplicates
            fraud_indicators=fraud_indicators,
            recommended_action=recommended_action,
            timestamp=datetime.now()
        )
        
        logger.info(f"Fraud detection for {claim_id}: score={fraud_score}, action={recommended_action}")
        
        return output

    def _load_fake_image_detector(self):
        """Load fake_image.py detector module from repository root if available."""
        try:
            repo_root = Path(__file__).resolve().parents[3]
            detector_path = repo_root / "fraud detection test" / "fake_image.py"
            if not detector_path.exists():
                logger.warning("fake_image.py not found at %s", detector_path)
                return None

            spec = importlib.util.spec_from_file_location("fake_image_detector", detector_path)
            if spec is None or spec.loader is None:
                logger.warning("Unable to create import spec for %s", detector_path)
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "run"):
                logger.warning("fake_image.py does not expose run(image_path, reference_dir=None)")
                return None
            logger.info("Loaded fake image detector from %s", detector_path)
            return module
        except Exception as exc:
            logger.warning("Failed to load fake image detector: %s", exc)
            return None

    def _resolve_local_image_path(self, media_link: str) -> Path | None:
        """Resolve local filesystem path from raw path or file:// URL."""
        if not media_link:
            return None

        raw = media_link.strip()
        candidate = Path(raw)
        if candidate.exists() and candidate.is_file():
            return candidate

        if raw.startswith("file://"):
            parsed = urlparse(raw)
            parsed_path = unquote(parsed.path or "")
            if parsed_path.startswith("/") and len(parsed_path) > 2 and parsed_path[2] == ":":
                parsed_path = parsed_path[1:]
            file_path = Path(parsed_path)
            if file_path.exists() and file_path.is_file():
                return file_path

        return None

    def _check_image_authenticity(self, media_links: List[str]) -> Tuple[int, List[str], Dict]:
        """Run fake image detection heuristics and convert results into fraud signals."""
        image_risk = 0
        flags: List[str] = []
        details: Dict[str, Any] = {
            "detector_loaded": bool(self.fake_image_detector),
            "media_links_received": len(media_links),
            "images_analyzed": 0,
            "results": [],
            "skipped": [],
        }

        if not media_links:
            details["reason"] = "No media links provided for forensic analysis"
            return image_risk, flags, details

        if not self.fake_image_detector:
            details["reason"] = "fake_image.py detector module not available"
            return image_risk, flags, details

        for media_link in media_links[:3]:
            local_path = self._resolve_local_image_path(media_link)
            if local_path is None:
                details["skipped"].append(
                    {
                        "media_link": media_link,
                        "reason": "Only local file paths are supported for forensic analysis",
                    }
                )
                continue

            try:
                result = self.fake_image_detector.run(local_path, reference_dir=None)
                details["images_analyzed"] += 1

                prediction = str(result.get("prediction", "unknown"))
                confidence = float(result.get("confidence", 0.0))
                details["results"].append(
                    {
                        "media_link": media_link,
                        "local_path": str(local_path),
                        "prediction": prediction,
                        "confidence": confidence,
                        "scores": result.get("scores", {}),
                        "metadata_chain_verification": result.get("metadata_chain_verification", {}),
                        "reasons": result.get("reasons", []),
                    }
                )

                if prediction == "ai_generated":
                    risk_delta = max(10, int(round(confidence * 25)))
                    image_risk += risk_delta
                    flags.append(f"Image appears AI-generated ({int(confidence * 100)}% confidence)")
                elif prediction == "edited":
                    risk_delta = max(6, int(round(confidence * 18)))
                    image_risk += risk_delta
                    flags.append(f"Image appears edited/manipulated ({int(confidence * 100)}% confidence)")

                meta_status = result.get("metadata_chain_verification", {}).get("status")
                if meta_status == "inconsistent":
                    image_risk += 8
                    flags.append("Image metadata chain is inconsistent")

            except Exception as exc:
                details["skipped"].append(
                    {
                        "media_link": media_link,
                        "reason": f"Detector failed: {exc}",
                    }
                )

        return image_risk, flags, details
    
    def _check_claim_history(self, policy_id: str, user_email: str) -> Tuple[int, List[str], Dict]:
        """Check user's claim history for patterns"""
        
        history_risk = 0
        flags = []
        details = {
            "claims_in_last_year": 0,
            "claims_in_last_6_months": 0,
            "frequency_risk": "low"
        }
        
        # Mock claim history
        if self.use_mock_db:
            # Simulate some claim history
            past_claims = self._get_mock_claim_history(policy_id)
        else:
            # Query actual database
            past_claims = self._query_claim_database(policy_id)
        
        now = datetime.now()
        
        # Count claims in different timeframes
        claims_1year = sum(1 for c in past_claims 
                          if (now - c).days <= 365)
        claims_6months = sum(1 for c in past_claims 
                            if (now - c).days <= 180)
        
        details["claims_in_last_year"] = claims_1year
        details["claims_in_last_6_months"] = claims_6months
        
        # Risk scoring
        if claims_6months > 2:
            history_risk += 25
            flags.append("Multiple claims in last 6 months")
            details["frequency_risk"] = "high"
        elif claims_1year > 3:
            history_risk += 15
            flags.append("High claim frequency in last year")
            details["frequency_risk"] = "medium"
        
        return history_risk, flags, details
    
    def _check_duplicate_claims(self, policy_id: str, incident_date: datetime, 
                               incident_location: str) -> Tuple[int, List[str], Dict]:
        """Check for duplicate or very similar claims"""
        
        duplicate_risk = 0
        flags = []
        details = {
            "similar_claims_found": 0,
            "days_since_similar_claim": None
        }
        
        # Get similar claims
        similar_claims = self._find_similar_claims(policy_id, incident_date, incident_location)
        
        details["similar_claims_found"] = len(similar_claims)
        
        if similar_claims:
            # Check if any very recent
            most_recent = min(similar_claims)
            days_diff = (incident_date - most_recent).days
            details["days_since_similar_claim"] = days_diff
            
            if days_diff < 7:
                duplicate_risk += 35
                flags.append(f"Duplicate claim detected (same location, {days_diff} days apart)")
            elif days_diff < 30:
                duplicate_risk += 15
                flags.append(f"Similar claim within last 30 days ({days_diff} days ago)")
        
        return duplicate_risk, flags, details
    
    def _check_description_mismatch(self, description: str, 
                                   damage_assessment: DamageAssessmentOutput) -> Tuple[int, List[str], Dict]:
        """Analyze mismatch between description and actual damage"""
        
        mismatch_risk = 0
        flags = []
        details = {
            "description_keywords": [],
            "damage_assessment_type": damage_assessment.damage_type,
            "mismatch_detected": False
        }
        
        # Extract keywords from description
        keywords = description.lower().split()
        details["description_keywords"] = keywords[:10]  # First 10 words
        
        # Check for severe inconsistencies
        damage_type_lower = damage_assessment.damage_type.lower()
        
        # If high severity damage but vague description
        if damage_assessment.severity_score > 70 and len(description) < 30:
            mismatch_risk += 10
            flags.append("High damage severity but vague description")
            details["mismatch_detected"] = True
        
        # If description mentions different damage type than detected
        severity_keywords = ["minor", "small", "scratch", "light"]
        critical_keywords = ["destroyed", "total loss", "severe", "critical"]
        
        has_minor_keyword = any(kw in keywords for kw in severity_keywords)
        has_critical_keyword = any(kw in keywords for kw in critical_keywords)
        
        if has_minor_keyword and damage_assessment.severity_score > 60:
            mismatch_risk += 15
            flags.append("Description claims minor damage but assessment shows high severity")
            details["mismatch_detected"] = True
        
        if has_critical_keyword and damage_assessment.severity_score < 40:
            mismatch_risk += 20
            flags.append("Description claims critical damage but assessment shows minor damage")
            details["mismatch_detected"] = True
        
        return mismatch_risk, flags, details
    
    def _check_metadata_consistency(self, incident_date: datetime, incident_location: str,
                                   damage_assessment: DamageAssessmentOutput) -> Tuple[int, List[str], Dict]:
        """Check metadata for inconsistencies"""
        
        metadata_risk = 0
        flags = []
        details = {
            "incident_date_valid": True,
            "location_provided": bool(incident_location),
            "image_metadata_check": True
        }
        
        # Check incident date is reasonable.
        # Normalize to timezone-aware UTC to avoid aware/naive comparison errors.
        if incident_date.tzinfo is None:
            incident_date_utc = incident_date.replace(tzinfo=timezone.utc)
        else:
            incident_date_utc = incident_date.astimezone(timezone.utc)

        now_utc = datetime.now(timezone.utc)

        if incident_date_utc > now_utc:
            metadata_risk += 30
            flags.append("Incident date is in the future")
            details["incident_date_valid"] = False
        
        if (now_utc - incident_date_utc).days > 90:
            metadata_risk += 10
            flags.append("Claim filed more than 90 days after incident")
        
        # Check location is provided
        if not incident_location or incident_location.strip() == "":
            metadata_risk += 5
            flags.append("Incident location not provided")
            details["location_provided"] = False
        
        # Check if visual analysis flagged fraud
        if damage_assessment.fraud_flag_visual:
            metadata_risk += 25
            flags.append("Visual analysis detected potential fraud indicators")
            details["image_metadata_check"] = False
        
        return metadata_risk, flags, details
    
    def _check_fraud_patterns(self, claim_id: str, policy_id: str,
                             damage_assessment: DamageAssessmentOutput,
                             description: str) -> Tuple[int, List[str], Dict]:
        """Check against known fraud patterns"""
        
        pattern_risk = 0
        flags = []
        details = {
            "patterns_matched": [],
            "known_fraud_indicators": []
        }
        
        # Pattern 1: Staged claims (common in motor insurance)
        if damage_assessment.damage_type == "dent" and damage_assessment.severity_score == 100:
            pattern_risk += 10
            flags.append("Unusual: Minor damage type but maximum severity")
            details["patterns_matched"].append("staged_claim_pattern")
        
        # Pattern 2: Over-reporting
        description_lower = description.lower()
        severity_inflation_keywords = ["destroyed", "total loss", "irreparable"]
        
        if any(kw in description_lower for kw in severity_inflation_keywords):
            if damage_assessment.severity_score < 80:
                pattern_risk += 15
                flags.append("Possible over-reporting: severe language but low damage score")
                details["patterns_matched"].append("over_reporting_pattern")
        
        # Pattern 3: Missing documentation pattern
        if len(description) < 20 and damage_assessment.severity_score > 50:
            pattern_risk += 8
            flags.append("Minimal documentation for significant damage")
            details["patterns_matched"].append("minimal_documentation_pattern")
        
        return pattern_risk, flags, details
    
    def _determine_action(self, fraud_score: int) -> str:
        """Determine recommended action based on fraud risk score"""
        
        if fraud_score >= config.FRAUD_CRITICAL_THRESHOLD:
            return "reject"
        elif fraud_score >= config.FRAUD_RISK_THRESHOLD:
            return "review"
        else:
            return "approve"
    
    def _get_mock_claim_history(self, policy_id: str) -> List[datetime]:
        """Get mock claim history for testing"""
        
        now = datetime.now()
        
        # Mock some claim history
        if policy_id.startswith("POL123"):
            # Policy with some history
            return [
                now - timedelta(days=10),
                now - timedelta(days=100),
                now - timedelta(days=250),
            ]
        else:
            # Policy with minimal history
            return [now - timedelta(days=365)]
    
    def _query_claim_database(self, policy_id: str) -> List[datetime]:
        """Query actual claim database - placeholder for production"""
        # In production, would query actual database
        return self._get_mock_claim_history(policy_id)
    
    def _find_similar_claims(self, policy_id: str, incident_date: datetime, 
                           incident_location: str) -> List[datetime]:
        """Find similar claims in history"""
        
        # Mock implementation
        mock_similar = [
            incident_date - timedelta(days=5),
        ]
        
        return mock_similar if policy_id.startswith("POL456") else []
    
    def _initialize_fraud_patterns(self) -> Dict[str, List[str]]:
        """Initialize known fraud patterns database"""
        
        return {
            "staged_claims": [
                "sequential_damage",
                "consistent_location",
                "same_time_patterns",
            ],
            "over_reporting": [
                "inflation_keywords",
                "exaggerated_damage",
                "unrealistic_costs",
            ],
            "organized_fraud": [
                "multiple_claimants",
                "related_claims",
                "suspicious_timing",
            ]
        }
    
    def get_audit_log(self, claim_id: str, policy_id: str = "unknown") -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="fraud_detection",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "policy_id": policy_id,
                "stage": "Fraud Detection"
            }
        )


# Initialize singleton instance
fraud_detection_agent = FraudDetectionAgent()


def detect_fraud(claim_id: str, policy_id: str, user_email: str,
                damage_assessment: DamageAssessmentOutput,
                incident_description: str,
                incident_date: datetime,
                incident_location: str,
                media_links: List[str] | None = None) -> FraudDetectionOutput:
    """
    Public function to detect fraud in claim.
    
    Args:
        claim_id: Unique claim identifier
        policy_id: Insurance policy ID
        user_email: Claimant email
        damage_assessment: Damage assessment output
        incident_description: Text description
        incident_date: Date of incident
        incident_location: Location of incident
        media_links: Uploaded media paths/URLs
        
    Returns:
        FraudDetectionOutput with fraud risk score
    """
    return fraud_detection_agent.detect_fraud(
        claim_id, policy_id, user_email, damage_assessment,
        incident_description, incident_date, incident_location, media_links
    )
