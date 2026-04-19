"""
Policy Understanding Agent - Policy coverage evaluation.
Parses policy rules and determines coverage validity.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from models.schemas import (
    PolicyAgentOutput, PolicyRule, AuditLogEntry, ClaimType
)

logger = logging.getLogger(__name__)


class PolicyUnderstandingAgent:
    """
    Agent responsible for understanding insurance policy coverage.
    
    Responsibilities:
    - Parse coverage rules
    - Extract covered scenarios, exclusions, limits, deductibles
    - Convert into structured logic
    """
    
    def __init__(self):
        self.agent_name = "Policy_Understanding_Agent"
        self.policy_database = {}  # In production, would be actual database
    
    def evaluate_policy_coverage(self, claim_id: str, policy_id: str, 
                                claim_type: ClaimType, 
                                policy_data: Optional[Dict[str, Any]] = None) -> PolicyAgentOutput:
        """
        Evaluate policy coverage for claim.
        
        Args:
            claim_id: Unique claim identifier
            policy_id: Insurance policy ID
            claim_type: Type of claim (motor/health/property)
            policy_data: Optional policy JSON data
            
        Returns:
            PolicyAgentOutput with coverage evaluation
        """
        logger.info(f"Evaluating policy {policy_id} for claim {claim_id}")
        
        # Load or retrieve policy
        if policy_data:
            policy = policy_data
        else:
            policy = self._load_policy(policy_id, claim_type)
        
        if not policy:
            logger.warning(f"Policy {policy_id} not found, using default coverage")
            return self._get_default_policy_output(claim_id)
        
        # Validate policy
        coverage_valid, issues = self._validate_policy(policy, claim_type)
        
        # Extract policy details
        max_claim_amount = policy.get("coverage", {}).get("max_claim_amount", 100000)
        deductible = policy.get("coverage", {}).get("deductible", 0)
        
        # Parse policy rules
        policy_rules = self._parse_policy_rules(policy)
        
        # Check for triggered exclusions
        exclusions_triggered = self._check_exclusions(policy, claim_type)
        
        output = PolicyAgentOutput(
            claim_id=claim_id,
            coverage_valid=coverage_valid,
            max_claim_amount=max_claim_amount,
            deductible=deductible,
            policy_rules=policy_rules,
            exclusions_triggered=exclusions_triggered,
            policy_details={
                "policy_id": policy_id,
                "claim_type": claim_type.value,
                "policy_status": policy.get("status", "active"),
                "policy_start_date": policy.get("start_date"),
                "policy_end_date": policy.get("end_date"),
                "coverage_issues": issues,
            },
            timestamp=datetime.now()
        )
        
        logger.info(f"Policy evaluation completed for {claim_id}: coverage_valid={coverage_valid}")
        
        return output
    
    def _load_policy(self, policy_id: str, claim_type: ClaimType) -> Optional[Dict[str, Any]]:
        """
        Load policy from database or storage.
        For production, this would query actual policy database.
        """
        # Check cache first
        if policy_id in self.policy_database:
            return self.policy_database[policy_id]
        
        # In production, would load from database
        # For now, return mock policy
        mock_policy = self._get_mock_policy(policy_id, claim_type)
        
        return mock_policy
    
    def _validate_policy(self, policy: Dict[str, Any], 
                        claim_type: ClaimType) -> Tuple[bool, List[str]]:
        """
        Validate policy is active and covers this claim type.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check policy status
        status = policy.get("status", "active")
        if status != "active":
            issues.append(f"Policy status is '{status}', not active")
        
        # Check policy dates
        today = datetime.now().date()
        start_date = policy.get("start_date")
        end_date = policy.get("end_date")
        
        if start_date and start_date > today:
            issues.append("Policy has not started yet")
        
        if end_date and end_date < today:
            issues.append("Policy has expired")
        
        # Check coverage for claim type
        covered_types = policy.get("coverage", {}).get("claim_types", [])
        if claim_type.value not in covered_types:
            issues.append(f"Claim type '{claim_type.value}' not covered by this policy")
        
        # Check premium paid
        if not policy.get("premium_paid", False):
            issues.append("Premium not fully paid")
        
        is_valid = len(issues) == 0
        
        return is_valid, issues
    
    def _parse_policy_rules(self, policy: Dict[str, Any]) -> List[PolicyRule]:
        """
        Parse policy rules into structured format.
        """
        rules = []
        
        # Parse coverage rules
        coverage = policy.get("coverage", {})
        
        if coverage.get("includes_collision", False):
            rules.append(PolicyRule(
                rule_id="collision_coverage",
                description="Covers collision damage",
                conditions={
                    "incident_type": "collision",
                    "max_amount": coverage.get("collision_limit", 500000)
                },
                action="apply_coverage"
            ))
        
        if coverage.get("includes_theft", False):
            rules.append(PolicyRule(
                rule_id="theft_coverage",
                description="Covers theft and burglary",
                conditions={
                    "incident_type": "theft",
                    "max_amount": coverage.get("theft_limit", 1000000)
                },
                action="apply_coverage"
            ))
        
        if coverage.get("includes_natural_disaster", False):
            rules.append(PolicyRule(
                rule_id="natural_disaster",
                description="Covers natural disasters",
                conditions={
                    "incident_type": ["flood", "earthquake", "cyclone"],
                    "max_amount": coverage.get("disaster_limit", 2000000)
                },
                action="apply_coverage"
            ))
        
        # Parse optional coverage
        if coverage.get("includes_roadside_assistance", False):
            rules.append(PolicyRule(
                rule_id="roadside_assistance",
                description="24/7 roadside assistance included",
                conditions={"service_type": "roadside"},
                action="provide_service"
            ))
        
        return rules
    
    def _check_exclusions(self, policy: Dict[str, Any], 
                         claim_type: ClaimType) -> List[str]:
        """
        Check if any policy exclusions are triggered.
        """
        exclusions = []
        
        exclusion_config = policy.get("exclusions", {})
        
        if exclusion_config.get("exclude_commercial_use", False):
            exclusions.append("Commercial use of vehicle excluded")
        
        if exclusion_config.get("exclude_racing", False):
            exclusions.append("Racing and high-speed driving excluded")
        
        if exclusion_config.get("exclude_valet", False):
            exclusions.append("Valet driving excluded")
        
        if exclusion_config.get("exclude_mechanical_breakdown", False):
            exclusions.append("Mechanical breakdown not covered")
        
        if exclusion_config.get("exclude_wear_tear", False):
            exclusions.append("Normal wear and tear not covered")
        
        return exclusions
    
    def _get_mock_policy(self, policy_id: str, claim_type: ClaimType) -> Dict[str, Any]:
        """Generate realistic mock policy for demo/testing"""
        
        base_policy = {
            "policy_id": policy_id,
            "status": "active",
            "start_date": (datetime.now() - timedelta(days=200)).date(),
            "end_date": (datetime.now() + timedelta(days=165)).date(),
            "premium_paid": True,
            "policyholder": "John Doe",
            "coverage": {
                "claim_types": ["motor", "health", "property"],
                "max_claim_amount": 500000,
                "deductible": 10000,
                "includes_collision": True,
                "includes_theft": True,
                "includes_natural_disaster": True,
                "includes_roadside_assistance": True,
                "collision_limit": 500000,
                "theft_limit": 1000000,
                "disaster_limit": 2000000,
            },
            "exclusions": {
                "exclude_commercial_use": True,
                "exclude_racing": True,
                "exclude_valet": False,
                "exclude_mechanical_breakdown": False,
                "exclude_wear_tear": False,
            },
            "riders": [
                "Accidental Damage Coverage",
                "Depreciation Waiver"
            ]
        }
        
        return base_policy
    
    def _get_default_policy_output(self, claim_id: str) -> PolicyAgentOutput:
        """
        Return default policy output when policy not found.
        Conservative approach - reduced coverage.
        """
        return PolicyAgentOutput(
            claim_id=claim_id,
            coverage_valid=False,
            max_claim_amount=0,
            deductible=0,
            policy_rules=[],
            exclusions_triggered=["Policy not found in system"],
            policy_details={
                "error": "Policy not found",
                "recommendation": "Manual review required"
            },
            timestamp=datetime.now()
        )
    
    def calculate_payout_from_policy(self, policy_output: PolicyAgentOutput, 
                                    damage_severity: int) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate payout amount based on policy and damage severity.
        
        Args:
            policy_output: PolicyAgentOutput with policy details
            damage_severity: Damage severity score (0-100)
            
        Returns:
            Tuple of (payout_amount, calculation_details)
        """
        
        # Estimate damage cost based on severity
        damage_cost_estimate = self._estimate_damage_cost(damage_severity)
        
        # Apply deductible
        claimable_amount = max(0, damage_cost_estimate - policy_output.deductible)
        
        # Cap at max coverage
        final_payout = min(claimable_amount, policy_output.max_claim_amount)
        
        calculation_details = {
            "damage_cost_estimate": damage_cost_estimate,
            "deductible": policy_output.deductible,
            "claimable_amount": claimable_amount,
            "max_coverage": policy_output.max_claim_amount,
            "final_payout": final_payout,
        }
        
        return final_payout, calculation_details
    
    def _estimate_damage_cost(self, severity_score: int) -> float:
        """
        Estimate damage cost based on severity score.
        This is simplified; production would use industry damage tables.
        """
        
        # Linear estimation: severity 100 = 500,000 INR max damage
        estimated_cost = (severity_score / 100) * 500000
        
        return estimated_cost
    
    def get_audit_log(self, claim_id: str, policy_id: Optional[str] = None) -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="policy_evaluation",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "policy_id": policy_id or "unknown",
                "stage": "Policy Understanding"
            }
        )


# Initialize singleton instance
policy_agent = PolicyUnderstandingAgent()


def evaluate_policy(claim_id: str, policy_id: str, claim_type: ClaimType,
                   policy_data: Optional[Dict[str, Any]] = None) -> PolicyAgentOutput:
    """
    Public function to evaluate policy coverage.
    
    Args:
        claim_id: Unique claim identifier
        policy_id: Insurance policy ID
        claim_type: Type of claim
        policy_data: Optional policy JSON data
        
    Returns:
        PolicyAgentOutput with coverage evaluation
    """
    return policy_agent.evaluate_policy_coverage(claim_id, policy_id, claim_type, policy_data)
