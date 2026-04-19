"""
Damage Assessment Agent - Vision-based damage analysis.
Uses Vertex AI Gemini models to analyze uploaded images/videos.
"""

import json
import base64
import requests
from typing import Dict, Any, List, Tuple
from datetime import datetime
import logging

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest

from models.schemas import (
    DamageAssessmentOutput, SeverityLevel, AuditLogEntry
)
from config.settings import config

logger = logging.getLogger(__name__)


class DamageAssessmentAgent:
    """
    Agent responsible for analyzing damage from uploaded media.
    
    Responsibilities:
    - Detect type of damage (scratch, dent, fracture, injury, etc.)
    - Estimate severity (low / medium / high)
    - Identify affected parts
    - Detect inconsistencies (fake or unrelated images)
    """
    
    def __init__(self):
        self.agent_name = "Damage_Assessment_Agent"
        self.project_id = config.VERTEX_AI_PROJECT_ID
        self.location = config.VERTEX_AI_LOCATION
        self.model = config.VERTEX_AI_MODEL
        self.use_mock = config.USE_MOCK_VISION_API
    
    def analyze_damages(self, claim_id: str, media_links: List[str], 
                       claim_type: str) -> DamageAssessmentOutput:
        """
        Analyze damages from media links.
        
        Args:
            claim_id: Unique claim identifier
            media_links: List of image/video URLs
            claim_type: Type of claim (motor/health/property)
            
        Returns:
            DamageAssessmentOutput with damage analysis
        """
        logger.info(f"Starting damage assessment for claim {claim_id}")
        
        if self.use_mock:
            return self._analyze_damages_mock(claim_id, media_links, claim_type)
        
        # Real Vertex AI Gemini analysis
        damage_analysis = []
        
        for media_link in media_links[:3]:  # Limit to 3 images for API cost control
            try:
                analysis = self._analyze_single_image(media_link, claim_type)
                damage_analysis.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {media_link}: {str(e)}")
                damage_analysis.append(self._get_fallback_analysis())
        
        # Aggregate results
        final_analysis = self._aggregate_analyses(claim_id, damage_analysis, claim_type)
        
        logger.info(f"Damage assessment completed for {claim_id}")
        
        return final_analysis
    
    def _analyze_single_image(self, image_url: str, claim_type: str) -> Dict[str, Any]:
        """
        Analyze a single image using Vertex AI Gemini.
        
        Args:
            image_url: URL to image
            claim_type: Type of claim
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Download image from URL
            image_data = self._download_image(image_url)
            
            # Create API request
            prompt = self._create_vision_prompt(claim_type)
            
            analysis = self._call_vertex_ai_vision_api(image_data, prompt)
            
            return analysis
        
        except Exception as e:
            logger.error(f"Vision API error: {str(e)}")
            return self._get_fallback_analysis()
    
    def _call_vertex_ai_vision_api(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """
        Call Vertex AI Gemini with image and prompt.
        """
        if not self.project_id:
            raise RuntimeError("VERTEX_AI_PROJECT_ID is not configured")

        # Encode image to base64
        encoded_image = base64.standard_b64encode(image_data).decode('utf-8')
        
        url = (
            f"https://{self.location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.project_id}/locations/{self.location}/publishers/google/"
            f"models/{self.model}:generateContent"
        )

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not credentials.valid:
            credentials.refresh(GoogleAuthRequest())
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}",
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": encoded_image
                        }
                    }
                ]
            }]
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Parse response
        analysis = self._parse_vision_response(result)
        
        return analysis
    
    def _parse_vision_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Vertex AI Gemini response"""
        try:
            content = response.get("candidates", [{}])[0].get("content", {})
            text = content.get("parts", [{}])[0].get("text", "")
            
            # Parse structured output from response
            analysis = self._extract_damage_info(text)
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error parsing vision response: {str(e)}")
            return self._get_fallback_analysis()
    
    def _extract_damage_info(self, response_text: str) -> Dict[str, Any]:
        """
        Extract structured damage information from API response text.
        """
        # This would parse the LLM response to extract:
        # - Damage type
        # - Severity score
        # - Affected components
        # - Fraud indicators
        
        # Simplified parsing logic
        analysis = {
            "damage_type": "unknown",
            "severity_score": 50,
            "affected_components": [],
            "confidence": 0.8,
            "fraud_flag": False,
        }
        
        response_lower = response_text.lower()
        
        # Simple keyword matching (production would use more sophisticated parsing)
        if "scratch" in response_lower:
            analysis["damage_type"] = "scratch"
            analysis["severity_score"] = 20
        elif "dent" in response_lower or "impact" in response_lower:
            analysis["damage_type"] = "dent"
            analysis["severity_score"] = 45
        elif "fracture" in response_lower or "break" in response_lower:
            analysis["damage_type"] = "fracture"
            analysis["severity_score"] = 75
        elif "bruise" in response_lower or "injury" in response_lower:
            analysis["damage_type"] = "injury"
            analysis["severity_score"] = 60
        
        # Fraud detection keywords
        if any(word in response_lower for word in ["fake", "photoshopped", "inconsistent", "unrelated"]):
            analysis["fraud_flag"] = True
        
        return analysis
    
    def _download_image(self, image_url: str) -> bytes:
        """Download image from URL"""
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    
    def _create_vision_prompt(self, claim_type: str) -> str:
        """Create detailed prompt for vision analysis based on claim type"""
        
        prompts = {
            "motor": """Analyze this vehicle damage image. Provide:
1. Type of damage (scratch, dent, glass damage, paint damage, etc.)
2. Severity level (1-100 scale, where 100 is total loss)
3. Affected components (bumper, door, window, etc.)
4. Estimated repair cost indicator
5. Any signs of fraud or inconsistency
Format as JSON with keys: damage_type, severity_score, components, confidence, fraud_indicators""",
            
            "health": """Analyze this medical/injury image. Provide:
1. Type of injury (fracture, laceration, bruise, burn, etc.)
2. Severity level (1-100 scale)
3. Affected body parts
4. Any signs of pre-existing condition or inconsistency
5. Medical urgency indicator
Format as JSON with keys: injury_type, severity_score, affected_parts, confidence, fraud_indicators""",
            
            "property": """Analyze this property damage image. Provide:
1. Type of damage (flood, fire, structural, theft, etc.)
2. Severity level (1-100 scale)
3. Affected areas/rooms
4. Estimated extent of damage
5. Any signs of deliberate damage or insurance fraud
Format as JSON with keys: damage_type, severity_score, affected_areas, confidence, fraud_indicators"""
        }
        
        return prompts.get(claim_type, prompts["motor"])
    
    def _analyze_damages_mock(self, claim_id: str, media_links: List[str], 
                             claim_type: str) -> DamageAssessmentOutput:
        """
        Mock analysis for development/testing.
        Returns realistic demo data.
        """
        
        mock_data = {
            "motor": {
                "damage_type": "dent",
                "severity_score": 45,
                "affected_components": ["front_bumper", "hood"],
                "confidence": 0.92,
                "fraud_flag": False,
            },
            "health": {
                "damage_type": "laceration",
                "severity_score": 35,
                "affected_components": ["left_arm"],
                "confidence": 0.88,
                "fraud_flag": False,
            },
            "property": {
                "damage_type": "water_damage",
                "severity_score": 60,
                "affected_components": ["basement", "walls"],
                "confidence": 0.85,
                "fraud_flag": False,
            }
        }
        
        data = mock_data.get(claim_type, mock_data["motor"])
        
        return DamageAssessmentOutput(
            claim_id=claim_id,
            damage_type=data["damage_type"],
            severity_score=data["severity_score"],
            severity_level=self._get_severity_level(data["severity_score"]),
            affected_components=data["affected_components"],
            confidence=data["confidence"],
            fraud_flag_visual=data["fraud_flag"],
            visual_details={
                "media_analyzed": len(media_links),
                "analysis_type": "mock_demo",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when API fails"""
        return {
            "damage_type": "unknown",
            "severity_score": 50,
            "affected_components": [],
            "confidence": 0.5,
            "fraud_flag": False,
        }
    
    def _aggregate_analyses(self, claim_id: str, analyses: List[Dict[str, Any]], 
                          claim_type: str) -> DamageAssessmentOutput:
        """Aggregate multiple image analyses into final assessment"""
        
        if not analyses:
            analyses = [self._get_fallback_analysis()]
        
        # Calculate averages and aggregates
        avg_severity = sum(a.get("severity_score", 50) for a in analyses) / len(analyses)
        avg_confidence = sum(a.get("confidence", 0.5) for a in analyses) / len(analyses)
        
        # Check if any image flagged fraud
        fraud_flagged = any(a.get("fraud_flag", False) for a in analyses)
        
        # Combine affected components
        all_components = []
        for analysis in analyses:
            all_components.extend(analysis.get("affected_components", []))
        unique_components = list(set(all_components))
        
        # Get most common damage type
        damage_types = [a.get("damage_type", "unknown") for a in analyses]
        damage_type = max(set(damage_types), key=damage_types.count)
        
        return DamageAssessmentOutput(
            claim_id=claim_id,
            damage_type=damage_type,
            severity_score=int(avg_severity),
            severity_level=self._get_severity_level(int(avg_severity)),
            affected_components=unique_components,
            confidence=avg_confidence,
            fraud_flag_visual=fraud_flagged,
            visual_details={
                "media_analyzed": len(analyses),
                "individual_analyses": analyses,
            },
            timestamp=datetime.now()
        )
    
    def _get_severity_level(self, score: int) -> SeverityLevel:
        """Convert severity score to level"""
        if score < 30:
            return SeverityLevel.LOW
        elif score < 70:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.HIGH
    
    def get_audit_log(self, claim_id: str) -> AuditLogEntry:
        """Generate audit log entry for this agent"""
        return AuditLogEntry(
            agent=self.agent_name,
            action="damage_assessment",
            timestamp=datetime.now(),
            details={
                "claim_id": claim_id,
                "stage": "Damage Assessment",
                "api_used": "Vertex AI Gemini"
            }
        )


# Initialize singleton instance
damage_assessment_agent = DamageAssessmentAgent()


def analyze_damages(claim_id: str, media_links: List[str], 
                   claim_type: str) -> DamageAssessmentOutput:
    """
    Public function to analyze damages.
    
    Args:
        claim_id: Unique claim identifier
        media_links: List of image/video URLs
        claim_type: Type of claim (motor/health/property)
        
    Returns:
        DamageAssessmentOutput with damage analysis
    """
    return damage_assessment_agent.analyze_damages(claim_id, media_links, claim_type)
