"""
FastAPI Backend for ClaimFast Insurance FNOL System.
Provides REST API for claim submission, status checking, and decision retrieval.
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
from datetime import datetime
from typing import List, Optional

from models.schemas import (
    ClaimSubmission, ClaimSubmissionResponse, ClaimStatusResponse,
    ClaimProcessingContext, UserDetails, ClaimType
)
from orchestrator import process_claim, get_claim_status, get_claim_details
from config.settings import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": config.API_VERSION,
        "environment": config.DEPLOYMENT_ENV
    }


# ============================================================================
# CLAIM SUBMISSION
# ============================================================================

@app.post("/api/v1/claims/submit", response_model=ClaimSubmissionResponse, tags=["Claims"])
async def submit_claim(
    background_tasks: BackgroundTasks,
    # User Details
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    policy_id: str = Form(...),
    # Claim Details
    claim_type: str = Form(...),
    incident_description: str = Form(...),
    incident_date: str = Form(...),
    incident_location: Optional[str] = Form(None),
    # Media Files
    media_files: List[UploadFile] = File(default=[])
):
    """
    Submit a new insurance claim.
    
    Request Parameters:
    - User details (name, email, phone, policy_id)
    - Claim type (motor/health/property)
    - Incident description and date
    - Incident location (optional)
    - Media files (images/videos) - up to 5 files
    
    Returns:
    - Claim ID for tracking
    - Processing status
    - Estimated processing time
    """
    
    try:
        logger.info(f"Received claim submission for policy {policy_id}")
        
        # Validate claim type
        try:
            claim_type_enum = ClaimType(claim_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid claim type. Supported: motor, health, property"
            )
        
        # Parse incident date
        try:
            from datetime import datetime
            incident_dt = datetime.fromisoformat(incident_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid incident date format. Use ISO 8601 format."
            )
        
        # Process media files (convert to mock URLs for demo)
        media_links = []
        for file in media_files[:5]:  # Limit to 5 files
            # In production, would upload to S3/Cloud Storage
            mock_url = f"https://storage.example.com/{file.filename}"
            media_links.append(mock_url)
            logger.info(f"Media file received: {file.filename}")
        
        # Create claim submission
        user_data = UserDetails(
            name=name,
            email=email,
            phone=phone,
            policy_id=policy_id
        )
        
        submission = ClaimSubmission(
            user_data=user_data,
            claim_type=claim_type_enum,
            incident_description=incident_description,
            incident_date=incident_dt,
            incident_location=incident_location,
            media_links=media_links
        )
        
        # Generate claim ID
        import uuid
        claim_id = f"CLM_{uuid.uuid4().hex[:12].upper()}"
        
        # Process claim asynchronously in background
        background_tasks.add_task(process_claim_async, claim_id, submission)
        
        response = ClaimSubmissionResponse(
            claim_id=claim_id,
            status="submitted",
            message="Claim submitted successfully. Processing has started.",
            timestamp=datetime.now()
        )
        
        logger.info(f"Claim {claim_id} submitted successfully")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting claim: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error submitting claim")


async def process_claim_async(claim_id: str, submission: ClaimSubmission):
    """Process claim asynchronously"""
    try:
        logger.info(f"Starting async processing for claim {claim_id}")
        await process_claim(submission)
    except Exception as e:
        logger.error(f"Error in async processing for {claim_id}: {str(e)}", exc_info=True)


# ============================================================================
# CLAIM STATUS & RETRIEVAL
# ============================================================================

@app.get("/api/v1/claims/{claim_id}/status", response_model=ClaimStatusResponse, tags=["Claims"])
async def get_claim_status_endpoint(claim_id: str):
    """
    Get the current status of a claim.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Current status, stage, progress, and decision if available
    """
    
    status = get_claim_status(claim_id)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Claim {claim_id} not found"
        )
    
    return status


@app.get("/api/v1/claims/{claim_id}/details", tags=["Claims"])
async def get_claim_details_endpoint(claim_id: str):
    """
    Get complete claim processing details including decision and audit trail.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Complete ClaimProcessingContext with all agent outputs
    """
    
    context = get_claim_details(claim_id)
    
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"Claim {claim_id} not found"
        )
    
    # Convert to JSON-serializable format
    return {
        "claim_id": context.claim_id,
        "status": "completed" if context.explainability_output else "processing",
        "decision": {
            "status": context.decision_output.final_decision.value if context.decision_output else None,
            "payout_amount": context.decision_output.payout_amount if context.decision_output else None,
            "reasoning": context.decision_output.reasoning if context.decision_output else None,
            "confidence": context.decision_output.confidence_score if context.decision_output else None,
        },
        "explanation": context.explainability_output.explanation_text if context.explainability_output else None,
        "audit_summary": {
            "total_agents": len(context.audit_trail),
            "stages": [entry.agent for entry in context.audit_trail],
            "processing_time": str(context.processing_end_time - context.processing_start_time) if context.processing_end_time else None,
        },
        "processing_start_time": context.processing_start_time.isoformat(),
        "processing_end_time": context.processing_end_time.isoformat() if context.processing_end_time else None,
    }


# ============================================================================
# DECISION & EXPLANATION
# ============================================================================

@app.get("/api/v1/claims/{claim_id}/decision", tags=["Claims"])
async def get_claim_decision(claim_id: str):
    """
    Get final claim decision with detailed explanation.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Decision status, payout, reasoning, and IRDAI-compliant explanation
    """
    
    context = get_claim_details(claim_id)
    
    if not context or not context.decision_output:
        raise HTTPException(
            status_code=404,
            detail=f"Decision for claim {claim_id} not found"
        )
    
    return {
        "claim_id": claim_id,
        "decision": context.decision_output.final_decision.value,
        "payout_amount": context.decision_output.payout_amount,
        "reasoning": context.decision_output.reasoning,
        "confidence_score": context.decision_output.confidence_score,
        "decision_factors": context.decision_output.decision_factors,
        "decision_timestamp": context.decision_output.timestamp.isoformat(),
    }


@app.get("/api/v1/claims/{claim_id}/explanation", tags=["Claims"])
async def get_claim_explanation(claim_id: str):
    """
    Get IRDAI-compliant explanation and audit trail.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Full explanation text and audit log
    """
    
    context = get_claim_details(claim_id)
    
    if not context or not context.explainability_output:
        raise HTTPException(
            status_code=404,
            detail=f"Explanation for claim {claim_id} not found"
        )
    
    return {
        "claim_id": claim_id,
        "explanation_text": context.explainability_output.explanation_text,
        "policy_clauses_used": context.explainability_output.policy_clauses_used,
        "damage_findings": context.explainability_output.damage_findings,
        "fraud_signals": context.explainability_output.fraud_signals,
        "compliance_status": context.explainability_output.compliance_status,
        "audit_log": [
            {
                "agent": entry.agent,
                "action": entry.action,
                "timestamp": entry.timestamp.isoformat(),
                "details": entry.details
            }
            for entry in context.explainability_output.audit_log
        ],
    }


# ============================================================================
# POLICY UPLOAD & MANAGEMENT
# ============================================================================

@app.post("/api/v1/policies/upload", tags=["Policies"])
async def upload_policy(
    policy_file: UploadFile = File(...)
):
    """
    Upload a policy JSON file.
    
    Expected format:
    {
        "policy_id": "POL123456",
        "status": "active",
        "coverage": {...},
        "exclusions": {...}
    }
    
    Args:
        policy_file: JSON file with policy definition
        
    Returns:
        Upload status and policy ID
    """
    
    try:
        content = await policy_file.read()
        import json
        
        policy_data = json.loads(content)
        
        if "policy_id" not in policy_data:
            raise HTTPException(
                status_code=400,
                detail="Policy must contain 'policy_id' field"
            )
        
        # In production, would store in database
        logger.info(f"Policy uploaded: {policy_data.get('policy_id')}")
        
        return {
            "status": "success",
            "policy_id": policy_data.get("policy_id"),
            "message": "Policy uploaded successfully"
        }
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"Error uploading policy: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading policy")


# ============================================================================
# ANALYTICS & REPORTING
# ============================================================================

@app.get("/api/v1/analytics/summary", tags=["Analytics"])
async def get_analytics_summary():
    """
    Get system analytics summary.
    
    Returns:
        Statistics about claim processing
    """
    
    # In production, would query database
    return {
        "system_uptime": "24 hours",
        "total_claims_processed": 0,  # Would query database
        "average_processing_time": "5.2 seconds",
        "approval_rate": "78%",
        "fraud_detection_rate": "3.2%",
        "system_status": "operational",
        "last_updated": datetime.now().isoformat(),
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on app startup"""
    logger.info(f"ClaimFast API starting (Environment: {config.DEPLOYMENT_ENV})")
    logger.info(f"Gemini Vision API: {'Mock' if config.USE_MOCK_VISION_API else 'Production'}")
    logger.info(f"CORS origins: {config.CORS_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    logger.info("ClaimFast API shutting down")


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ClaimFast FNOL System",
        "version": config.API_VERSION,
        "description": "Automated First Notice of Loss insurance claim processing",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "endpoints": {
            "health": "/health",
            "submit_claim": "POST /api/v1/claims/submit",
            "claim_status": "GET /api/v1/claims/{claim_id}/status",
            "claim_details": "GET /api/v1/claims/{claim_id}/details",
            "claim_decision": "GET /api/v1/claims/{claim_id}/decision",
            "claim_explanation": "GET /api/v1/claims/{claim_id}/explanation",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
