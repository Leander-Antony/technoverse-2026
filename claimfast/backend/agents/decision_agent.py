"""
Decision Agent - Final claim decision logic.
Combines all agent outputs and determines approval/rejection/review.
"""

from typing import Dict, Any, Tuple
from datetime import datetime
import logging

from models.schemas import (
    DecisionOutput, DecisionStatus, IntakeAgentOutput, 
    DamageAssessmentOutput, PolicyAgentOutput, FraudDetectionOutput, AuditLogEntry
)
from config.settings import config

logger = logging.getLogger(__name__)


class DecisionAgent:
    """
    Core decision-making agent.
    
    Responsibilities:
    - Combine all agent outputs
    - Apply decision logic
    - Calculate payout amount
    """
    
    def __init__(self):
        self.agent_name = "Decision_Agent"
    
    def make_decision(self, 
                     intake_output: IntakeAgentOutput,
                     damage_output: DamageAssessmentOutput,
                     policy_output: PolicyAgentOutput,
                     fraud_output: FraudDetectionOutput) -> DecisionOutput:
        """
        Make final claim decision based on all agent outputs.
        
        Args:
            intake_output: FNOL intake validation
            damage_output: Damage assessment from vision
            policy_output: Policy coverage evaluation
            fraud_output: Fraud risk assessment
            
        Returns:
            DecisionOutput with final decision and payout
        """
        
        claim_id = intake_output.claim_id
        logger.info(f"Making decision for claim {claim_id}")
        
        # Decision logic
        decision, decision_factors = self._apply_decision_logic(
            intake_output, damage_output, policy_output, fraud_output
        )
        
        # Calculate payout
        if decision == DecisionStatus.APPROVED:
            payout_amount = self._calculate_payout(damage_output, policy_output)
        else:
            payout_amount = 0.0
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            decision, decision_factors, damage_output, policy_output, fraud_output
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            damage_output, policy_output, fraud_output
        )
        
        output = DecisionOutput(
            claim_id=claim_id,
            final_decision=decision,
            payout_amount=payout_amount,
            reasoning=reasoning,
            confidence_score=confidence,
            decision_factors=decision_factors,
            timestamp=datetime.now()
        )
        
        logger.info(f"Decision for {claim_id}: {decision.value} | Payout: ₹{payout_amount}")
        
        return output
    
    def _apply_decision_logic(self,
                             intake_output: IntakeAgentOutput,
                             damage_output: DamageAssessmentOutput,
                             policy_output: PolicyAgentOutput,
                             fraud_output: FraudDetectionOutput) -> Tuple[DecisionStatus, Dict[str, Any]]:
        """
        Apply decision logic rules.
        
        Decision Tree:
        1. If intake validation failed → REJECT
        2. If policy not valid → REJECT
        3. If fraud score critical (≥80) → REJECT
        4. If fraud score high (≥60) OR exclusion triggered → MANUAL_REVIEW
        5. Otherwise → APPROVED (if damage reasonable)
        """
        
        factors = {
            "intake_valid": intake_output.status == "validated",
            "policy_valid": policy_output.coverage_valid,
            "fraud_score": fraud_output.fraud_risk_score,
            "exclusions_triggered": len(policy_output.exclusions_triggered) > 0,
            "damage_confidence": damage_output.confidence,
        }
        
        # Rule 1: Intake validation must pass
        if intake_output.status != "validated":
            return DecisionStatus.REJECTED, factors
        
        # Rule 2: Policy must be valid
        if not policy_output.coverage_valid:
            return DecisionStatus.REJECTED, factors
        
        # Rule 3: Critical fraud risk
        if fraud_output.fraud_risk_score >= config.FRAUD_CRITICAL_THRESHOLD:
            return DecisionStatus.REJECTED, factors
        
        # Rule 4: High fraud risk or exclusions triggered
        if (fraud_output.fraud_risk_score >= config.FRAUD_RISK_THRESHOLD or 
            len(policy_output.exclusions_triggered) > 0):
            return DecisionStatus.MANUAL_REVIEW, factors
        
        # Rule 5: Approve with confidence check
        if damage_output.confidence < 0.5:
            return DecisionStatus.MANUAL_REVIEW, factors
        
        # Default: Approve
        return DecisionStatus.APPROVED, factors
    
    def _calculate_payout(self, damage_output: DamageAssessmentOutput,
                         policy_output: PolicyAgentOutput) -> float:
        """
        Calculate payout amount.
        
        Formula:
        payout = min(max_claim_amount, estimated_damage - deductible)
        """
        
        # Estimate damage cost based on severity
        # Simplified: severity 100 = 500,000 INR damage
        estimated_damage_cost = (damage_output.severity_score / 100) * 500000
        
        # Apply deductible
        claimable_amount = max(0, estimated_damage_cost - policy_output.deductible)
        
        # Cap at maximum coverage
        final_payout = min(claimable_amount, policy_output.max_claim_amount)
        
        # Round to nearest 100
        final_payout = round(final_payout / 100) * 100
        
        return final_payout
    
    def _generate_reasoning(self, decision: DecisionStatus,
                           factors: Dict[str, Any],
                           damage_output: DamageAssessmentOutput,
                           policy_output: PolicyAgentOutput,
                           fraud_output: FraudDetectionOutput) -> str:
        """Generate human-readable explanation of decision"""
        
        reasoning_parts = []
        
        # Add decision statement
        if decision == DecisionStatus.APPROVED:
            reasoning_parts.append("✓ CLAIM APPROVED")
        elif decision == DecisionStatus.REJECTED:
            reasoning_parts.append("✗ CLAIM REJECTED")
        else:
            reasoning_parts.append("⚠ CLAIM REQUIRES MANUAL REVIEW")
        
        # Add key factors
        reasoning_parts.append(f"\nDamage Assessment:")
        reasoning_parts.append(f"  • Type: {damage_output.damage_type}")
        reasoning_parts.append(f"  • Severity: {damage_output.severity_level.value} ({damage_output.severity_score}/100)")
        reasoning_parts.append(f"  • Confidence: {damage_output.confidence:.1%}")
        
        reasoning_parts.append(f"\nPolicy Coverage:")
        if policy_output.coverage_valid:
            reasoning_parts.append(f"  • Status: ACTIVE")
            reasoning_parts.append(f"  • Max Coverage: ₹{policy_output.max_claim_amount:,.0f}")
            reasoning_parts.append(f"  • Deductible: ₹{policy_output.deductible:,.0f}")
        else:
            reasoning_parts.append(f"  • Status: NOT VALID")
            for issue in policy_output.policy_details.get("coverage_issues", []):
                reasoning_parts.append(f"  • {issue}")
        
        reasoning_parts.append(f"\nFraud Assessment:")
        reasoning_parts.append(f"  • Risk Score: {fraud_output.fraud_risk_score}/100")
        if fraud_output.fraud_flags:
            reasoning_parts.append(f"  • Flags: {len(fraud_output.fraud_flags)} detected")
            for flag in fraud_output.fraud_flags[:3]:  # Show first 3
                reasoning_parts.append(f"    - {flag}")
        else:
            reasoning_parts.append(f"  • Status: No fraud indicators")
        
        if decision == DecisionStatus.REJECTED:
            reasoning_parts.append(f"\nRejection Reason:")
            if not factors["intake_valid"]:
                reasoning_parts.append("  • Intake validation failed")
            elif not factors["policy_valid"]:
                reasoning_parts.append("  • Policy does not cover this claim")
            elif factors["fraud_score"] >= config.FRAUD_CRITICAL_THRESHOLD:
                reasoning_parts.append(f"  • Critical fraud risk detected (score: {factors['fraud_score']})")
        
        return "\n".join(reasoning_parts)
    
    def _calculate_confidence(self, damage_output: DamageAssessmentOutput,
                            policy_output: PolicyAgentOutput,
                            fraud_output: FraudDetectionOutput) -> float:
        """
        Calculate overall confidence score (0-1) for decision.
        """
        
        # Start with damage assessment confidence
        confidence = damage_output.confidence * 0.5
        
        # Add policy validity bonus
        if policy_output.coverage_valid:
            confidence += 0.25
        
        # Subtract fraud risk
        fraud_factor = 1 - (fraud_output.fraud_risk_score / 100)
        confidence += fraud_factor * 0.25
        
        # Cap at 1.0
        confidence = min(confidence, 1.0)
        
        return confidence
    
    def get_audit_log(self, claim_id: str) -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="decision_making",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "stage": "Decision Making"
            }
        )


# Initialize singleton instance
decision_agent = DecisionAgent()


def make_decision(intake_output: IntakeAgentOutput,
                 damage_output: DamageAssessmentOutput,
                 policy_output: PolicyAgentOutput,
                 fraud_output: FraudDetectionOutput) -> DecisionOutput:
    """
    Public function to make final claim decision.
    
    Args:
        intake_output: FNOL intake validation
        damage_output: Damage assessment
        policy_output: Policy coverage
        fraud_output: Fraud detection
        
    Returns:
        DecisionOutput with final decision
    """
    return decision_agent.make_decision(intake_output, damage_output, policy_output, fraud_output)
