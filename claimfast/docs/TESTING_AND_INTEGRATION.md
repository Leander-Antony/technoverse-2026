# ClaimFast - Integration Testing & Usage Guide

## 🧪 Testing Guide

### Unit Tests

```bash
# Run all unit tests
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/test_intake_agent.py -v

# Run with coverage
pytest tests/ --cov=agents --cov=models --cov-report=html
```

### Integration Tests

```bash
# Full pipeline test
pytest tests/test_pipeline_integration.py -v

# Test with real Vertex AI Gemini
USE_MOCK_VISION_API=false pytest tests/test_damage_assessment.py -v

# Load testing
locust -f tests/locustfile.py --host=http://localhost:8000
```

### Manual Testing

#### 1. Submit Claim via API

```bash
# Using curl
curl -X POST "http://localhost:8000/api/v1/claims/submit" \
  -H "Content-Type: multipart/form-data" \
  -F "name=John Doe" \
  -F "email=john@example.com" \
  -F "phone=9876543210" \
  -F "policy_id=POL123456" \
  -F "claim_type=motor" \
  -F "incident_description=Car collision at intersection" \
  -F "incident_date=2024-01-15T08:30:00" \
  -F "incident_location=NH48, Bangalore" \
  -F "media_files=@/path/to/image1.jpg" \
  -F "media_files=@/path/to/image2.jpg"

# Expected Response:
# {
#   "claim_id": "CLM_ABC123DEF456",
#   "status": "submitted",
#   "message": "Claim submitted successfully",
#   "timestamp": "2024-01-15T10:30:45Z"
# }
```

#### 2. Poll Claim Status

```bash
# Get claim status
curl -X GET "http://localhost:8000/api/v1/claims/CLM_ABC123DEF456/status"

# Expected Response:
# {
#   "claim_id": "CLM_ABC123DEF456",
#   "status": "APPROVED",
#   "current_stage": "Explainability",
#   "progress_percentage": 100,
#   "latest_decision": "approved",
#   "payout_amount": 195000,
#   "last_updated": "2024-01-15T11:05:00Z"
# }
```

#### 3. Get Final Decision

```bash
# Get decision details
curl -X GET "http://localhost:8000/api/v1/claims/CLM_ABC123DEF456/decision"

# Expected Response includes:
# - decision: approved/rejected/manual_review
# - payout_amount: final approved amount
# - reasoning: detailed explanation
# - confidence_score: 0-1
# - decision_factors: all contributing factors
```

#### 4. Get Full Explanation

```bash
# Get IRDAI-compliant explanation
curl -X GET "http://localhost:8000/api/v1/claims/CLM_ABC123DEF456/explanation"

# Response includes:
# - explanation_text: full decision explanation
# - audit_log: all processing stages
# - policy_clauses_used: relevant policy terms
# - damage_findings: vision analysis results
# - compliance_status: IRDAI-ready
```

---

## 🚀 End-to-End Usage Workflow

### 1. User Submits Claim (Browser/Mobile App)

```
Frontend: Claim Submission Form
├─ User enters details (name, phone, email, policy_id)
├─ Selects claim type (motor/health/property)
├─ Enters incident description and date
├─ Uploads 1-5 images/videos
└─ Clicks "Submit Claim"

API Endpoint: POST /api/v1/claims/submit
Returns: claim_id + status message
```

### 2. Backend Processing Pipeline

```
Backend Orchestrator receives request
│
├─→ Stage 1: FNOL Intake Agent (~1-2 sec)
│   ├─ Validates all input fields
│   ├─ Checks email, phone format
│   ├─ Verifies media files
│   └─ Generates unique claim_id
│
├─→ Stage 2: Damage Assessment Agent (~15-20 sec)
│   ├─ Sends images to Vertex AI Gemini
│   ├─ Gets damage classification
│   ├─ Calculates severity score
│   └─ Flags potential fraud indicators
│
├─→ Stage 3: Policy Understanding Agent (~2-3 sec)
│   ├─ Loads policy from database
│   ├─ Validates coverage for claim type
│   ├─ Extracts deductible and limits
│   └─ Checks exclusions
│
├─→ Stage 4: Fraud Detection Agent (~3-5 sec)
│   ├─ Checks claim history
│   ├─ Looks for duplicates
│   ├─ Analyzes description mismatch
│   └─ Scores fraud risk (0-100)
│
├─→ Stage 5: Decision Agent (~1-2 sec)
│   ├─ Applies decision logic
│   ├─ Calculates payout
│   └─ Generates confidence score
│
└─→ Stage 6: Explainability Agent (~2-3 sec)
    ├─ Creates human-readable explanation
    ├─ Compiles audit trail
    ├─ Ensures IRDAI compliance
    └─ Returns complete response

Total: 25-35 seconds (< 60-second target ✓)
```

### 3. Real-Time Status Updates (Frontend)

```javascript
// Frontend polls for status every 2 seconds
const pollStatus = setInterval(async () => {
  const response = await fetch(
    `/api/v1/claims/${claimId}/status`
  );
  const status = await response.json();
  
  // Update UI with:
  // - Current stage
  // - Progress percentage
  // - Latest decision (when available)
  
  if (status.progress_percentage === 100) {
    clearInterval(pollStatus); // Stop polling
    showFinalDecision();
  }
}, 2000);
```

### 4. User Views Decision & Explanation

```
Frontend: Decision Screen
├─ Final Decision Banner (APPROVED/REJECTED/REVIEW)
├─ Payout Amount (if approved)
├─ Confidence Score
├─ Decision Reasoning
├─ Policy Clauses Used
├─ Damage Findings
├─ Fraud Assessment
├─ Audit Trail
└─ Next Steps
```

---

## 📊 Test Scenarios

### Scenario 1: Approved Claim (Motor)

```
Input:
- Policy: Active motor comprehensive
- Damage: Medium (collision, 45/100)
- Fraud Risk: Low (15/100)

Expected Output:
- Decision: APPROVED
- Payout: ₹195,000
- Time: 30 seconds
```

### Scenario 2: Rejected Claim (High Fraud Risk)

```
Input:
- Policy: Active but has exclusion
- Damage: High (100/100) with fraud flags
- Fraud Risk: Critical (85/100)

Expected Output:
- Decision: REJECTED
- Payout: ₹0
- Reason: Critical fraud risk
```

### Scenario 3: Manual Review (Medium Risk)

```
Input:
- Policy: Valid coverage
- Damage: Moderate (60/100)
- Fraud Risk: Medium-high (65/100)

Expected Output:
- Decision: MANUAL_REVIEW
- Escalation: To human underwriter
- Next Step: Manual assessment
```

---

## 🔍 Debugging Guide

### Enable Debug Logging

```python
# backend/.env
DEBUG=true
LANGCHAIN_DEBUG=true
LOG_LEVEL=DEBUG
```

### Check Processing Stages

```bash
# View backend logs
docker-compose logs -f backend

# Stream specific agent logs
docker-compose logs backend | grep "Damage_Assessment_Agent"
```

### Validate API Responses

```bash
# Check health endpoint
curl http://localhost:8000/health

# View Swagger documentation
curl http://localhost:8000/api/docs

# Export OpenAPI schema
curl http://localhost:8000/openapi.json > schema.json
```

---

## 🔧 Troubleshooting

### Issue: Vision API Timeout

```
Error: Vertex AI Gemini request timeout
```

**Solution:**
```python
# Increase timeout in config/settings.py
AGENT_TIMEOUTS = {
    "damage_assessment": 45,  # Increased from 30
}
```

### Issue: Database Connection

```
Error: Failed to connect to database
```

**Solution:**
```bash
# Check database is running
docker-compose ps

# View database logs
docker-compose logs db

# Verify connection string
echo $DATABASE_URL
```

### Issue: CORS Errors

```
Error: Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
```python
# Update backend/config/settings.py
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://yourdomain.com",  # Add your domain
]
```

---

## 📈 Performance Metrics

### Capture Performance Data

```python
# backend/utils/metrics.py

import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__}: {elapsed:.2f}s")
        return result
    return wrapper

# Usage
@measure_time
def analyze_damages(claim_id, media_links):
    # ... processing code
    pass
```

### Expected Times

```
FNOL Intake:        1-2 seconds    ✓ Very fast
Damage Assessment:  15-25 seconds  ✓ API dependent
Policy Evaluation:  2-3 seconds    ✓ Very fast
Fraud Detection:    3-5 seconds    ✓ Fast
Decision Making:    1-2 seconds    ✓ Very fast
Explainability:     2-3 seconds    ✓ Very fast
────────────────────────────────────────
Total:              25-40 seconds  ✓ Under 60s target
```

---

## ✅ Pre-Deployment Checklist

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Load testing passed (100+ concurrent claims)
- [ ] API documentation complete
- [ ] Error handling verified
- [ ] Logging configured
- [ ] Database migrations applied
- [ ] API keys configured
- [ ] CORS enabled for production domains
- [ ] SSL/TLS certificates installed
- [ ] Monitoring dashboards created
- [ ] Backup strategy verified
- [ ] Disaster recovery tested
- [ ] IRDAI compliance verified
- [ ] Security audit completed

---

## 📞 Support

For issues or questions:
- Open GitHub Issue
- Email: support@claimfast.com
- Slack: #claimfast-support

