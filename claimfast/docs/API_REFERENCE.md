# ClaimFast API Reference

## Base URL
```
Development: http://localhost:8000
Production: https://api.claimfast.com
```

## Authentication
Currently uses optional Bearer token. Production deployment should implement JWT authentication.

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/claims/submit
```

---

## 📝 Endpoints Overview

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/claims/submit` | Submit new claim | 100ms |
| GET | `/api/v1/claims/{id}/status` | Get processing status | 50ms |
| GET | `/api/v1/claims/{id}/details` | Get full claim context | 75ms |
| GET | `/api/v1/claims/{id}/decision` | Get final decision | 50ms |
| GET | `/api/v1/claims/{id}/explanation` | Get explanation | 50ms |
| POST | `/api/v1/policies/upload` | Upload policy | 200ms |
| GET | `/api/v1/analytics/summary` | System analytics | 100ms |
| GET | `/health` | Health check | 10ms |
| GET | `/` | API info | 10ms |

---

## 🔌 Detailed Endpoint Documentation

### 1. Submit Claim

Submit a new insurance claim with supporting documents.

**Endpoint:** `POST /api/v1/claims/submit`

**Request Headers:**
```
Content-Type: multipart/form-data
Authorization: Bearer token (optional)
```

**Request Body (Form Data):**
```
name                    string    required  Name of claimant
email                   string    required  Email address
phone                   string    required  10-15 digit phone number
policy_id               string    required  Insurance policy ID
claim_type              string    required  motor|health|property
incident_description    string    required  Description of incident (min 10 chars)
incident_date          datetime   required  ISO 8601 format
incident_location      string    optional  Location of incident
media_files            file[]     required  1-5 image/video files (max 50MB each)
```

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/claims/submit" \
  -H "Content-Type: multipart/form-data" \
  -F "name=John Doe" \
  -F "email=john@example.com" \
  -F "phone=9876543210" \
  -F "policy_id=POL_MOTOR_001" \
  -F "claim_type=motor" \
  -F "incident_description=Vehicle collision at traffic junction" \
  -F "incident_date=2024-01-15T08:30:00" \
  -F "incident_location=NH48, Bangalore" \
  -F "media_files=@damage_photo_1.jpg" \
  -F "media_files=@damage_photo_2.jpg"
```

**Example Request (Python):**
```python
import requests

url = "http://localhost:8000/api/v1/claims/submit"

files = [
    ('media_files', open('damage_1.jpg', 'rb')),
    ('media_files', open('damage_2.jpg', 'rb')),
]

data = {
    'name': 'John Doe',
    'email': 'john@example.com',
    'phone': '9876543210',
    'policy_id': 'POL_MOTOR_001',
    'claim_type': 'motor',
    'incident_description': 'Vehicle collision',
    'incident_date': '2024-01-15T08:30:00',
    'incident_location': 'NH48, Bangalore',
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Successful Response (201 Created):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "status": "submitted",
  "message": "Claim submitted successfully. Processing will begin shortly.",
  "timestamp": "2024-01-15T10:30:00Z",
  "processing_url": "/api/v1/claims/CLM_MOTOR_2024_001/status",
  "estimated_processing_time_seconds": 45
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Validation error",
  "details": [
    {
      "field": "email",
      "issue": "Invalid email format"
    },
    {
      "field": "phone",
      "issue": "Phone number must be 10-15 digits"
    }
  ]
}
```

**Validation Rules:**
- Email: Must be valid email format (RFC 5322)
- Phone: 10-15 digits, no spaces or special characters
- Policy ID: Must exist in database (mock: POL_MOTOR_001, POL_HEALTH_001, POL_PROPERTY_001)
- Description: Minimum 10 characters
- Date: Cannot be in future
- Media: JPG, PNG, MP4 only; max 50MB per file; 1-5 files required

---

### 2. Get Claim Status

Poll for current processing status and progress.

**Endpoint:** `GET /api/v1/claims/{claim_id}/status`

**Path Parameters:**
```
claim_id    string    required    Claim ID returned from submit endpoint
```

**Response (200 OK):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "status": "PROCESSING",
  "current_stage": "Damage Assessment",
  "progress_percentage": 40,
  "stages_completed": [
    "FNOL Intake"
  ],
  "stages_remaining": [
    "Damage Assessment",
    "Policy Evaluation",
    "Fraud Detection",
    "Decision Making",
    "Explainability"
  ],
  "time_elapsed_seconds": 8,
  "estimated_time_remaining_seconds": 25,
  "latest_decision": null,
  "last_updated": "2024-01-15T10:30:08Z"
}
```

**When Complete (Status = APPROVED/REJECTED/MANUAL_REVIEW):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "status": "APPROVED",
  "current_stage": "Complete",
  "progress_percentage": 100,
  "stages_completed": [
    "FNOL Intake",
    "Damage Assessment",
    "Policy Evaluation",
    "Fraud Detection",
    "Decision Making",
    "Explainability"
  ],
  "time_elapsed_seconds": 35,
  "latest_decision": {
    "decision": "approved",
    "payout_amount": 195000,
    "confidence_score": 0.94
  },
  "last_updated": "2024-01-15T10:31:05Z"
}
```

**Polling Recommendation:**
```javascript
// Poll every 2 seconds until complete
const interval = setInterval(async () => {
  const response = await fetch(
    `/api/v1/claims/${claimId}/status`
  );
  const data = await response.json();
  
  console.log(`Progress: ${data.progress_percentage}%`);
  
  if (data.progress_percentage === 100) {
    clearInterval(interval);
    // Navigate to decision screen
  }
}, 2000);
```

---

### 3. Get Full Claim Details

Retrieve complete claim processing context.

**Endpoint:** `GET /api/v1/claims/{claim_id}/details`

**Response (200 OK):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "original_submission": {
    "name": "John Doe",
    "email": "john@example.com",
    "policy_id": "POL_MOTOR_001",
    "claim_type": "motor",
    "incident_description": "Vehicle collision",
    "media_links": ["https://..."]
  },
  "intake_output": {
    "validation_status": "validated",
    "claim_id": "CLM_MOTOR_2024_001"
  },
  "damage_assessment_output": {
    "damage_type": "collision_front_end",
    "severity_score": 45,
    "confidence": 0.92,
    "affected_components": ["front_bumper", "windshield"]
  },
  "policy_output": {
    "coverage_valid": true,
    "max_claim_amount": 500000,
    "deductible": 10000
  },
  "fraud_output": {
    "fraud_risk_score": 15,
    "fraud_flags": []
  },
  "decision_output": {
    "final_decision": "approved",
    "payout_amount": 195000,
    "confidence_score": 0.94
  },
  "explainability_output": {
    "explanation_text": "...",
    "compliance_status": "IRDAI-ready"
  }
}
```

---

### 4. Get Final Decision

Get the final claim decision with reasoning.

**Endpoint:** `GET /api/v1/claims/{claim_id}/decision`

**Response (200 OK):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "final_decision": "approved",
  "decision_status": "final",
  "payout_calculation": {
    "estimated_damage_cost": 225000,
    "less_deductible": 10000,
    "less_depreciation": 20000,
    "final_approved_payout": 195000,
    "currency": "INR"
  },
  "confidence_score": 0.94,
  "decision_reasoning": "Claim is valid. Vehicle collision damage confirmed through image analysis (severity 45/100). Policy provides full collision coverage. No fraud indicators detected.",
  "contributing_factors": {
    "damage_assessment": "FAVORABLE",
    "policy_coverage": "COVERED",
    "fraud_risk": "LOW",
    "policy_status": "ACTIVE"
  },
  "timeline": {
    "submitted_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:31:05Z",
    "processing_duration_seconds": 35
  }
}
```

---

### 5. Get Explanation

Retrieve IRDAI-compliant decision explanation.

**Endpoint:** `GET /api/v1/claims/{claim_id}/explanation`

**Response (200 OK):**
```json
{
  "claim_id": "CLM_MOTOR_2024_001",
  "explanation_summary": "APPROVED - ₹195,000 payout authorized",
  "explanation_text": "Full IRDAI-compliant detailed explanation with all reasoning...",
  "policy_clauses_used": [
    {
      "clause_id": "COL_001",
      "clause_title": "Collision Coverage",
      "clause_text": "Full coverage for accidental collision damage"
    },
    {
      "clause_id": "DED_001",
      "clause_title": "Deductible",
      "clause_text": "₹10,000 deductible applies"
    }
  ],
  "damage_findings": {
    "damage_type": "Collision - Front End",
    "severity_score": 45,
    "affected_components": ["front_bumper", "windshield", "hood"],
    "visual_confidence": 0.92,
    "fraud_indicators": "None detected"
  },
  "audit_log": [
    {
      "timestamp": "2024-01-15T10:30:01Z",
      "stage": "FNOL_Intake",
      "action": "claim_validation",
      "status": "success"
    },
    {
      "timestamp": "2024-01-15T10:30:15Z",
      "stage": "Damage_Assessment",
      "action": "vision_analysis",
      "status": "success",
      "details": "severity_45_damage"
    },
    {
      "timestamp": "2024-01-15T10:30:25Z",
      "stage": "Policy_Evaluation",
      "action": "coverage_check",
      "status": "success",
      "details": "collision_covered"
    },
    {
      "timestamp": "2024-01-15T10:30:30Z",
      "stage": "Fraud_Detection",
      "action": "risk_assessment",
      "status": "success",
      "details": "fraud_score_15_low_risk"
    },
    {
      "timestamp": "2024-01-15T10:30:35Z",
      "stage": "Decision_Engine",
      "action": "decision_logic",
      "status": "success",
      "details": "approved_payout_195000"
    },
    {
      "timestamp": "2024-01-15T10:31:05Z",
      "stage": "Explainability",
      "action": "compliance_check",
      "status": "success",
      "details": "irdai_ready"
    }
  ],
  "compliance_status": "IRDAI-ready",
  "next_steps": [
    "Payment will be processed within 5 business days",
    "Submit original repair invoices",
    "Provide bank account details for transfer"
  ]
}
```

---

### 6. Upload Policy

Upload a new insurance policy (Admin endpoint).

**Endpoint:** `POST /api/v1/policies/upload`

**Request Body (JSON):**
```json
{
  "policy_id": "POL_NEW_001",
  "policy_type": "motor_comprehensive",
  "coverage": {
    "max_claim_amount": 500000,
    "deductible": 10000,
    "includes_collision": true
  },
  "exclusions": {
    "exclude_racing": true,
    "exclude_commercial_use": true
  }
}
```

**Response (201 Created):**
```json
{
  "policy_id": "POL_NEW_001",
  "status": "uploaded",
  "message": "Policy uploaded successfully"
}
```

---

### 7. System Analytics

Get system-wide analytics and statistics.

**Endpoint:** `GET /api/v1/analytics/summary`

**Response (200 OK):**
```json
{
  "total_claims_processed": 1234,
  "claims_today": 45,
  "approval_rate": 0.73,
  "rejection_rate": 0.12,
  "manual_review_rate": 0.15,
  "average_processing_time_seconds": 32,
  "fastest_claim_seconds": 12,
  "slowest_claim_seconds": 58,
  "fraud_detection_accuracy": 0.96,
  "uptime_percentage": 99.9,
  "top_claim_types": [
    {
      "type": "motor",
      "count": 800,
      "percentage": 65
    },
    {
      "type": "health",
      "count": 300,
      "percentage": 24
    },
    {
      "type": "property",
      "count": 134,
      "percentage": 11
    }
  ]
}
```

---

### 8. Health Check

Verify API is online and operational.

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:35:00Z",
  "version": "1.0.0",
  "environment": "production",
  "database": "connected",
  "cache": "connected",
  "vision_api": "available"
}
```

---

## 🔑 Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 200 | OK | Success |
| 201 | Created | Claim submitted successfully |
| 400 | Bad Request | Check input validation |
| 401 | Unauthorized | Provide valid API token |
| 404 | Not Found | Claim ID doesn't exist |
| 422 | Unprocessable Entity | Invalid data format |
| 429 | Too Many Requests | Rate limited, retry later |
| 500 | Server Error | Contact support |
| 503 | Service Unavailable | System maintenance |

---

## 🧪 Quick Test Script

```python
#!/usr/bin/env python3
"""ClaimFast API Test Script"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_submit_claim():
    """Test claim submission"""
    url = f"{BASE_URL}/api/v1/claims/submit"
    
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '9876543210',
        'policy_id': 'POL_MOTOR_001',
        'claim_type': 'motor',
        'incident_description': 'Test collision damage',
        'incident_date': '2024-01-15T08:30:00',
    }
    
    files = [
        ('media_files', open('sample_image.jpg', 'rb')),
    ]
    
    response = requests.post(url, data=data, files=files)
    print(f"Submit: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.json()['claim_id']

def test_get_status(claim_id):
    """Poll claim status"""
    url = f"{BASE_URL}/api/v1/claims/{claim_id}/status"
    
    import time
    for i in range(20):
        response = requests.get(url)
        data = response.json()
        progress = data['progress_percentage']
        print(f"Progress: {progress}%")
        
        if progress == 100:
            break
        time.sleep(2)

def test_get_decision(claim_id):
    """Get final decision"""
    url = f"{BASE_URL}/api/v1/claims/{claim_id}/decision"
    response = requests.get(url)
    print(f"Decision: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    print("🚀 ClaimFast API Test\n")
    
    # 1. Submit claim
    print("1️⃣ Submitting claim...")
    claim_id = test_submit_claim()
    
    # 2. Poll status
    print("\n2️⃣ Polling status...")
    test_get_status(claim_id)
    
    # 3. Get decision
    print("\n3️⃣ Getting decision...")
    test_get_decision(claim_id)
    
    print("\n✅ Test complete!")
```

---

## 📚 Additional Resources

- [Architecture Guide](./ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Testing Guide](./TESTING_AND_INTEGRATION.md)
- [OpenAPI Swagger](http://localhost:8000/api/docs)
- [ReDoc Documentation](http://localhost:8000/api/redoc)

