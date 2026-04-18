"""
Pipeline Orchestrator - Coordinates all agents in the claim processing pipeline.
Implements the 4-stage processing flow.
"""

import asyncio
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

from models.schemas import (
    ClaimSubmission, ClaimProcessingContext, ClaimStatusResponse,
    ClaimType, AuditLogEntry
)

from agents.intake_agent import process_intake
from agents.damage_assessment_agent import analyze_damages
from agents.policy_agent import evaluate_policy
from agents.fraud_detection_agent import detect_fraud
from agents.decision_agent import make_decision
from agents.explainability_agent import generate_explanation

logger = logging.getLogger(__name__)


class ClaimProcessingOrchestrator:
    """
    Orchestrates the complete claim processing pipeline.
    Coordinates 6 agents in sequence.
    
    Pipeline:
    1. FNOL Intake Agent - Validate input
    2. Damage Assessment Agent - Analyze images
    3. Policy Understanding Agent - Check coverage
    4. Fraud Detection Agent - Risk scoring
    5. Decision Agent - Final decision
    6. Explainability Agent - Audit & compliance
    """
    
    def __init__(self):
        self.orchestrator_name = "ClaimFast_Orchestrator"
        # In production, would use Redis or database
        self.claim_storage = {}  # In-memory storage for demo
        self.processing_contexts = {}  # Track all processing contexts
    
    async def process_claim_end_to_end(self, 
                                       submission: ClaimSubmission) -> ClaimProcessingContext:
        """
        Process a claim end-to-end through all 6 agents.
        
        Target: Complete processing in < 60 seconds
        
        Args:
            submission: ClaimSubmission with claim data
            
        Returns:
            ClaimProcessingContext with complete processing results
        """
        
        start_time = time.time()
        
        # Initialize context
        claim_id = f"CLM_{uuid.uuid4().hex[:12].upper()}"
        context = ClaimProcessingContext(
            claim_id=claim_id,
            original_submission=submission,
            processing_start_time=datetime.now()
        )
        
        logger.info(f"Starting end-to-end processing for claim {claim_id}")
        print(f"\n🚀 Processing Claim: {claim_id}")
        print("=" * 70)
        
        try:
            # Stage 1: FNOL Intake
            print("\n📋 Stage 1: FNOL Intake Validation...")
            context.intake_output = await self._stage_1_intake(submission, context)
            
            if context.intake_output.status == "validation_failed":
                context.processing_end_time = datetime.now()
                logger.warning(f"Intake validation failed for {claim_id}")
                return context
            
            print(f"✓ Intake validated. Claim ID: {claim_id}")
            
            # Stage 2: Damage Assessment
            print("\n🔍 Stage 2: Damage Assessment (Vision)...")
            context.damage_assessment_output = await self._stage_2_damage_assessment(
                context
            )
            print(f"✓ Damage assessed: {context.damage_assessment_output.damage_type} "
                  f"({context.damage_assessment_output.severity_score}/100)")
            
            # Stage 3: Policy Evaluation
            print("\n📋 Stage 3: Policy Coverage Evaluation...")
            context.policy_output = await self._stage_3_policy_evaluation(context)
            print(f"✓ Policy evaluated: Coverage {'VALID' if context.policy_output.coverage_valid else 'INVALID'}")
            
            # Stage 4: Fraud Detection
            print("\n🔐 Stage 4: Fraud Risk Detection...")
            context.fraud_detection_output = await self._stage_4_fraud_detection(context)
            print(f"✓ Fraud assessment: {context.fraud_detection_output.fraud_risk_score}/100 "
                  f"({context.fraud_detection_output.recommended_action})")
            
            # Stage 5: Decision Making
            print("\n⚖️ Stage 5: Final Decision...")
            context.decision_output = await self._stage_5_decision(context)
            print(f"✓ Decision: {context.decision_output.final_decision.value.upper()} | "
                  f"Payout: ₹{context.decision_output.payout_amount:,.0f}")
            
            # Stage 6: Explainability & Audit
            print("\n📄 Stage 6: Explainability & Compliance...")
            context.explainability_output = await self._stage_6_explainability(context)
            print(f"✓ Explanation generated (IRDAI-ready)")
            
            context.processing_end_time = datetime.now()
            
            # Calculate total time
            processing_time = time.time() - start_time
            print("\n" + "=" * 70)
            print(f"✅ CLAIM PROCESSING COMPLETE")
            print(f"Total Processing Time: {processing_time:.2f} seconds")
            print(f"Target: < 60 seconds | Status: {'✓ PASSED' if processing_time < 60 else '✗ EXCEEDED'}")
            print("=" * 70 + "\n")
            
            # Store claim
            self.claim_storage[claim_id] = context
            
            logger.info(f"Claim {claim_id} processed successfully in {processing_time:.2f}s")
            
            return context
        
        except Exception as e:
            logger.error(f"Error processing claim {claim_id}: {str(e)}", exc_info=True)
            context.processing_end_time = datetime.now()
            raise
    
    async def _stage_1_intake(self, submission: ClaimSubmission,
                             context: ClaimProcessingContext) -> Any:
        """Stage 1: FNOL Intake Validation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, process_intake, submission)
    
    async def _stage_2_damage_assessment(self, 
                                        context: ClaimProcessingContext) -> Any:
        """Stage 2: Damage Assessment (Vision)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            analyze_damages,
            context.claim_id,
            context.intake_output.media_links,
            context.intake_output.claim_type.value
        )
    
    async def _stage_3_policy_evaluation(self, 
                                        context: ClaimProcessingContext) -> Any:
        """Stage 3: Policy Coverage Evaluation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            evaluate_policy,
            context.claim_id,
            context.intake_output.user_data.policy_id,
            context.intake_output.claim_type,
            None  # Policy data - None to use default/DB
        )
    
    async def _stage_4_fraud_detection(self,
                                      context: ClaimProcessingContext) -> Any:
        """Stage 4: Fraud Risk Detection"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            detect_fraud,
            context.claim_id,
            context.intake_output.user_data.policy_id,
            context.intake_output.user_data.email,
            context.damage_assessment_output,
            context.intake_output.incident_summary,
            context.original_submission.incident_date,
            context.original_submission.incident_location or "Not specified"
        )
    
    async def _stage_5_decision(self, context: ClaimProcessingContext) -> Any:
        """Stage 5: Final Decision"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            make_decision,
            context.intake_output,
            context.damage_assessment_output,
            context.policy_output,
            context.fraud_detection_output
        )
    
    async def _stage_6_explainability(self,
                                     context: ClaimProcessingContext) -> Any:
        """Stage 6: Explainability & Audit"""
        
        # Build audit trail
        audit_trail = []
        
        # Add entries from each agent
        from agents.intake_agent import intake_agent
        from agents.damage_assessment_agent import damage_assessment_agent
        from agents.policy_agent import policy_agent
        from agents.fraud_detection_agent import fraud_detection_agent
        from agents.decision_agent import decision_agent
        from agents.explainability_agent import explainability_agent
        
        agents = [
            intake_agent, damage_assessment_agent, policy_agent,
            fraud_detection_agent, decision_agent, explainability_agent
        ]
        
        for agent in agents:
            audit_trail.append(agent.get_audit_log(context.claim_id))
        
        context.audit_trail = audit_trail
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            generate_explanation,
            context.claim_id,
            context.decision_output,
            context.intake_output,
            context.damage_assessment_output,
            context.policy_output,
            context.fraud_detection_output,
            audit_trail
        )
    
    def get_claim_status(self, claim_id: str) -> Optional[ClaimStatusResponse]:
        """Get status of a claim"""
        
        if claim_id not in self.claim_storage:
            return None
        
        context = self.claim_storage[claim_id]
        
        # Determine current stage
        stage = "Initialization"
        progress = 0
        
        if context.intake_output:
            stage = "Intake Validation"
            progress = 15
        if context.damage_assessment_output:
            stage = "Damage Assessment"
            progress = 30
        if context.policy_output:
            stage = "Policy Evaluation"
            progress = 45
        if context.fraud_detection_output:
            stage = "Fraud Detection"
            progress = 60
        if context.decision_output:
            stage = "Decision Making"
            progress = 75
        if context.explainability_output:
            stage = "Complete"
            progress = 100
        
        status_map = {
            "approved": "APPROVED",
            "rejected": "REJECTED",
            "manual_review": "MANUAL_REVIEW"
        }
        
        return ClaimStatusResponse(
            claim_id=claim_id,
            status=status_map.get(context.decision_output.final_decision.value, "PROCESSING")
            if context.decision_output else "PROCESSING",
            current_stage=stage,
            progress_percentage=progress,
            latest_decision=context.decision_output.final_decision if context.decision_output else None,
            payout_amount=context.decision_output.payout_amount if context.decision_output else None,
            last_updated=context.processing_end_time or datetime.now()
        )
    
    def get_claim_details(self, claim_id: str) -> Optional[ClaimProcessingContext]:
        """Get full claim processing context"""
        return self.claim_storage.get(claim_id)


# Initialize singleton
orchestrator = ClaimProcessingOrchestrator()


async def process_claim(submission: ClaimSubmission) -> ClaimProcessingContext:
    """
    Public async function to process a claim end-to-end.
    """
    return await orchestrator.process_claim_end_to_end(submission)


def get_claim_status(claim_id: str) -> Optional[ClaimStatusResponse]:
    """Public function to get claim status"""
    return orchestrator.get_claim_status(claim_id)


def get_claim_details(claim_id: str) -> Optional[ClaimProcessingContext]:
    """Public function to get full claim details"""
    return orchestrator.get_claim_details(claim_id)
