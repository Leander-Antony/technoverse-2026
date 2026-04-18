"""
Explainability & Audit Agent - IRDAI compliance and audit trail.
Generates human-readable explanations and maintains audit logs.
"""

from typing import Dict, Any, List
from datetime import datetime
import json
import logging

from models.schemas import (
    ExplainabilityOutput, AuditLogEntry, DecisionOutput, 
    DamageAssessmentOutput, PolicyAgentOutput, FraudDetectionOutput,
    IntakeAgentOutput
)

logger = logging.getLogger(__name__)


class ExplainabilityAgent:
    """
    Agent responsible for generating explainable outputs.
    
    Responsibilities:
    - Convert decision into human-readable explanation
    - Include policy clauses used, damage findings, fraud signals
    - Store full audit log for compliance
    - Ensure IRDAI compliance
    """
    
    def __init__(self):
        self.agent_name = "Explainability_Agent"
    
    def generate_explanation(self,
                            claim_id: str,
                            decision_output: DecisionOutput,
                            intake_output: IntakeAgentOutput,
                            damage_output: DamageAssessmentOutput,
                            policy_output: PolicyAgentOutput,
                            fraud_output: FraudDetectionOutput,
                            audit_trail: List[AuditLogEntry]) -> ExplainabilityOutput:
        """
        Generate IRDAI-compliant explanation and audit trail.
        
        Args:
            claim_id: Unique claim identifier
            decision_output: Final decision from decision agent
            intake_output: Intake validation output
            damage_output: Damage assessment output
            policy_output: Policy evaluation output
            fraud_output: Fraud detection output
            audit_trail: List of audit log entries
            
        Returns:
            ExplainabilityOutput with complete audit and explanation
        """
        
        logger.info(f"Generating explanation for claim {claim_id}")
        
        # Generate human-readable explanation
        explanation_text = self._generate_explanation_text(
            decision_output, intake_output, damage_output, 
            policy_output, fraud_output
        )
        
        # Extract policy clauses used
        policy_clauses = self._extract_policy_clauses(policy_output)
        
        # Extract damage findings
        damage_findings = self._extract_damage_findings(damage_output)
        
        # Extract fraud signals
        fraud_signals = self._extract_fraud_signals(fraud_output)
        
        # Add final audit entries
        full_audit_trail = audit_trail + [
            self.get_audit_log(claim_id)
        ]
        
        # Create IRDAI compliance statement
        compliance_status = "IRDAI-ready"
        
        output = ExplainabilityOutput(
            claim_id=claim_id,
            explanation_text=explanation_text,
            audit_log=full_audit_trail,
            policy_clauses_used=policy_clauses,
            damage_findings=damage_findings,
            fraud_signals=fraud_signals,
            compliance_status=compliance_status,
            timestamp=datetime.now()
        )
        
        logger.info(f"Explanation generated for {claim_id}")
        
        return output
    
    def _generate_explanation_text(self, decision_output: DecisionOutput,
                                   intake_output: IntakeAgentOutput,
                                   damage_output: DamageAssessmentOutput,
                                   policy_output: PolicyAgentOutput,
                                   fraud_output: FraudDetectionOutput) -> str:
        """Generate comprehensive explanation text"""
        
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("CLAIM DECISION EXPLANATION & JUSTIFICATION")
        lines.append(f"Claim ID: {decision_output.claim_id}")
        lines.append(f"Decision Date: {decision_output.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        # Decision Summary
        lines.append("\n1. FINAL DECISION")
        lines.append("-" * 70)
        decision_text = {
            "approved": "✓ APPROVED - Claim is approved for payment",
            "rejected": "✗ REJECTED - Claim is not approved",
            "manual_review": "⚠ MANUAL REVIEW REQUIRED - Claim requires further review"
        }
        lines.append(f"Status: {decision_text.get(decision_output.final_decision.value, 'Unknown')}")
        
        if decision_output.payout_amount > 0:
            lines.append(f"Approved Payout: ₹{decision_output.payout_amount:,.2f}")
        else:
            lines.append(f"Approved Payout: ₹0 (No payout)")
        
        lines.append(f"Confidence: {decision_output.confidence_score:.1%}")
        
        # Claim Details
        lines.append("\n2. CLAIM DETAILS")
        lines.append("-" * 70)
        lines.append(f"Claimant: {intake_output.user_data.name}")
        lines.append(f"Policy ID: {intake_output.user_data.policy_id}")
        lines.append(f"Claim Type: {intake_output.claim_type.value.upper()}")
        lines.append(f"Incident Summary: {intake_output.incident_summary}")
        
        # Damage Assessment
        lines.append("\n3. DAMAGE ASSESSMENT")
        lines.append("-" * 70)
        lines.append(f"Damage Type: {damage_output.damage_type}")
        lines.append(f"Severity Level: {damage_output.severity_level.value.upper()} ({damage_output.severity_score}/100)")
        lines.append(f"Affected Components: {', '.join(damage_output.affected_components)}")
        lines.append(f"Assessment Confidence: {damage_output.confidence:.1%}")
        
        if damage_output.fraud_flag_visual:
            lines.append(f"Visual Fraud Indicators: DETECTED")
        else:
            lines.append(f"Visual Fraud Indicators: None detected")
        
        # Policy Coverage
        lines.append("\n4. POLICY COVERAGE ANALYSIS")
        lines.append("-" * 70)
        coverage_status = "VALID" if policy_output.coverage_valid else "INVALID"
        lines.append(f"Coverage Status: {coverage_status}")
        lines.append(f"Maximum Claim Amount: ₹{policy_output.max_claim_amount:,.2f}")
        lines.append(f"Deductible: ₹{policy_output.deductible:,.2f}")
        
        if policy_output.exclusions_triggered:
            lines.append(f"Exclusions Triggered: {len(policy_output.exclusions_triggered)}")
            for i, exclusion in enumerate(policy_output.exclusions_triggered, 1):
                lines.append(f"  {i}. {exclusion}")
        else:
            lines.append("Exclusions Triggered: None")
        
        # Fraud Risk Assessment
        lines.append("\n5. FRAUD RISK ASSESSMENT")
        lines.append("-" * 70)
        lines.append(f"Fraud Risk Score: {fraud_output.fraud_risk_score}/100")
        
        risk_level = self._get_fraud_risk_level(fraud_output.fraud_risk_score)
        lines.append(f"Risk Level: {risk_level}")
        
        if fraud_output.fraud_flags:
            lines.append(f"Fraud Flags: {len(fraud_output.fraud_flags)}")
            for i, flag in enumerate(fraud_output.fraud_flags[:5], 1):  # Show top 5
                lines.append(f"  {i}. {flag}")
        else:
            lines.append("Fraud Flags: None detected")
        
        # Recommendation
        lines.append("\n6. DECISION REASONING")
        lines.append("-" * 70)
        lines.append(decision_output.reasoning)
        
        # IRDAI Compliance Statement
        lines.append("\n7. IRDAI COMPLIANCE STATEMENT")
        lines.append("-" * 70)
        lines.append("""This decision has been generated by ClaimFast - an automated FNOL
system compliant with IRDAI guidelines. The decision is based on:
  • Automated intake validation
  • Image-based damage assessment (Gemini Vision API)
  • Policy rules engine
  • Fraud risk analysis
  • Decision tree logic with manual review escalation

A complete audit trail is maintained for all processing stages.
This claim remains subject to final underwriter verification.""")
        
        # Footer with timestamp
        lines.append("\n" + "=" * 70)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _extract_policy_clauses(self, policy_output: PolicyAgentOutput) -> List[str]:
        """Extract policy clauses used in decision"""
        
        clauses = []
        
        # Add policy rules as clauses
        for rule in policy_output.policy_rules:
            clauses.append(rule.description)
        
        # Add coverage information
        if policy_output.coverage_valid:
            clauses.append(
                f"Maximum coverage of ₹{policy_output.max_claim_amount:,.0f} applies to this claim"
            )
            clauses.append(
                f"Applicable deductible of ₹{policy_output.deductible:,.0f}"
            )
        
        # Add exclusions
        for exclusion in policy_output.exclusions_triggered:
            clauses.append(f"Exclusion applies: {exclusion}")
        
        return clauses
    
    def _extract_damage_findings(self, damage_output: DamageAssessmentOutput) -> Dict[str, Any]:
        """Extract key damage findings"""
        
        return {
            "damage_type": damage_output.damage_type,
            "severity_level": damage_output.severity_level.value,
            "severity_score": damage_output.severity_score,
            "affected_components": damage_output.affected_components,
            "assessment_confidence": damage_output.confidence,
            "visual_fraud_indicators": damage_output.fraud_flag_visual,
            "analysis_timestamp": damage_output.timestamp.isoformat(),
        }
    
    def _extract_fraud_signals(self, fraud_output: FraudDetectionOutput) -> List[str]:
        """Extract fraud risk signals"""
        
        signals = []
        
        # Add fraud score information
        signals.append(f"Fraud Risk Score: {fraud_output.fraud_risk_score}/100")
        
        # Add individual flags
        signals.extend(fraud_output.fraud_flags)
        
        # Add recommendation
        signals.append(f"Recommended Action: {fraud_output.recommended_action}")
        
        return signals
    
    def _get_fraud_risk_level(self, score: int) -> str:
        """Get human-readable fraud risk level"""
        
        if score < 20:
            return "Very Low"
        elif score < 40:
            return "Low"
        elif score < 60:
            return "Medium"
        elif score < 80:
            return "High"
        else:
            return "Critical"
    
    def generate_audit_report(self, claim_id: str, 
                            audit_trail: List[AuditLogEntry]) -> Dict[str, Any]:
        """
        Generate detailed audit report for compliance.
        """
        
        return {
            "claim_id": claim_id,
            "total_agents_involved": len(set(entry.agent for entry in audit_trail)),
            "processing_stages": [entry.agent for entry in audit_trail],
            "total_processing_time": self._calculate_processing_time(audit_trail),
            "audit_entries": [
                {
                    "agent": entry.agent,
                    "action": entry.action,
                    "timestamp": entry.timestamp.isoformat(),
                    "details": entry.details
                }
                for entry in audit_trail
            ],
            "report_generated": datetime.now().isoformat(),
        }
    
    def _calculate_processing_time(self, audit_trail: List[AuditLogEntry]) -> str:
        """Calculate total processing time"""
        
        if not audit_trail:
            return "0 seconds"
        
        start_time = min(entry.timestamp for entry in audit_trail)
        end_time = max(entry.timestamp for entry in audit_trail)
        
        delta = end_time - start_time
        seconds = delta.total_seconds()
        
        if seconds < 1:
            return f"{int(seconds * 1000)} milliseconds"
        elif seconds < 60:
            return f"{int(seconds)} seconds"
        else:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
    
    def get_audit_log(self, claim_id: str) -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="explanation_generation",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "stage": "Explainability & Audit",
                "compliance": "IRDAI-ready"
            }
        )


# Initialize singleton instance
explainability_agent = ExplainabilityAgent()


def generate_explanation(claim_id: str,
                        decision_output: DecisionOutput,
                        intake_output: IntakeAgentOutput,
                        damage_output: DamageAssessmentOutput,
                        policy_output: PolicyAgentOutput,
                        fraud_output: FraudDetectionOutput,
                        audit_trail: List[AuditLogEntry]) -> ExplainabilityOutput:
    """
    Public function to generate explanation.
    
    Args:
        claim_id: Unique claim identifier
        decision_output: Final decision
        intake_output: Intake validation
        damage_output: Damage assessment
        policy_output: Policy evaluation
        fraud_output: Fraud detection
        audit_trail: Processing audit trail
        
    Returns:
        ExplainabilityOutput with full explanation and audit
    """
    return explainability_agent.generate_explanation(
        claim_id, decision_output, intake_output, damage_output,
        policy_output, fraud_output, audit_trail
    )
