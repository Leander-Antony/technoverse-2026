# ClaimFast - Deployment Guide

## 📋 Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [AWS Lambda Deployment](#aws-lambda-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Logging](#monitoring--logging)
7. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- **Python 3.9+**
- **Node.js 16+ and npm**
- **Git**
- **Virtual environment tool** (venv, conda)
- **Google Cloud project with Vertex AI enabled**

### Step 1: Clone Repository

```bash
cd d:\Desktop\_\Git\technoverse-2026
git clone https://github.com/yourusername/claimfast.git
cd claimfast
```

### Step 2: Setup Backend

#### Create Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Configure Environment Variables

Create `backend/.env` file:

```env
# API Configuration
DEPLOYMENT_ENV=development
LOG_LEVEL=INFO

# Vertex AI
VERTEX_AI_PROJECT_ID=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash-002
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json

# Vision API (use mock for development)
USE_MOCK_VISION_API=true
USE_MOCK_FRAUD_DB=true

# Database (optional for development)
DATABASE_URL=sqlite:///./claimfast.db

# CORS Configuration
# Configured in config/settings.py
```

#### Run Backend Server

```bash
# Development with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (no reload)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`
- API Docs: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Step 3: Setup Frontend

#### Install Frontend Dependencies

```bash
cd frontend
npm install
```

#### Configure API Endpoint

Edit `frontend/src/config/api.js`:

```javascript
export const API_BASE_URL = 'http://localhost:8000';
```

#### Run Development Server

```bash
npm start
```

Frontend will be available at: `http://localhost:3000`

### Step 4: Test Claim Submission

1. Open `http://localhost:3000` in browser
2. Fill out claim form
3. Upload test images (included in `data/sample_claims/`)
4. Submit claim
5. View real-time processing status
6. Check decision and explanation

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Build and Run

#### 1. Create Docker Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DEPLOYMENT_ENV: production
      VERTEX_AI_PROJECT_ID: ${VERTEX_AI_PROJECT_ID}
      VERTEX_AI_LOCATION: ${VERTEX_AI_LOCATION}
      VERTEX_AI_MODEL: ${VERTEX_AI_MODEL}
      GOOGLE_APPLICATION_CREDENTIALS: ${GOOGLE_APPLICATION_CREDENTIALS}
      USE_MOCK_VISION_API: "false"
    volumes:
      - ./backend/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    depends_on:
      - backend

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### 2. Create Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 3. Create Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:16-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# Production image
FROM node:16-alpine

WORKDIR /app

# Install serve
RUN npm install -g serve

# Copy built app
COPY --from=builder /app/build ./build

# Expose port
EXPOSE 3000

# Run
CMD ["serve", "-s", "build", "-l", "3000"]
```

#### 4. Deploy with Docker Compose

```bash
# Set Vertex AI project credentials
export VERTEX_AI_PROJECT_ID=your_project_id
export VERTEX_AI_LOCATION=us-central1

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

## AWS Lambda Deployment

### Prerequisites

- AWS CLI configured
- AWS SAM CLI
- S3 bucket for code storage
- IAM role with Lambda permissions

### Step 1: Create SAM Template

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2010-05-13

Globals:
  Function:
    Timeout: 60
    MemorySize: 512
    Environment:
      Variables:
        DEPLOYMENT_ENV: production
        VERTEX_AI_PROJECT_ID: !Ref VertexAiProjectId
        VERTEX_AI_LOCATION: !Ref VertexAiLocation
        VERTEX_AI_MODEL: !Ref VertexAiModel
        GOOGLE_APPLICATION_CREDENTIALS: !Ref GoogleApplicationCredentials
        USE_MOCK_VISION_API: "false"

Parameters:
  VertexAiProjectId:
    Type: String
    NoEcho: true
  VertexAiLocation:
    Type: String
    Default: us-central1
  VertexAiModel:
    Type: String
    Default: gemini-1.5-flash-002
  GoogleApplicationCredentials:
    Type: String
    NoEcho: true

Resources:
  ClaimFastFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: main.handler
      Runtime: python3.11
      Events:
        SubmitClaim:
          Type: Api
          Properties:
            RestApiId: !Ref ClaimFastApi
            Path: /api/v1/claims/submit
            Method: POST
        GetStatus:
          Type: Api
          Properties:
            RestApiId: !Ref ClaimFastApi
            Path: /api/v1/claims/{id}/status
            Method: GET
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - s3:GetObject
                - s3:PutObject
              Resource: !Sub '${MediaBucket.Arn}/*'
            - Effect: Allow
              Action:
                - dynamodb:GetItem
                - dynamodb:PutItem
              Resource: !GetAtt ClaimTable.Arn

  ClaimFastApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      TracingEnabled: true

  MediaBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: claimfast-media-${AWS::AccountId}

  ClaimTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: ClaimFast-Claims
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: claim_id
          AttributeType: S
      KeySchema:
        - AttributeName: claim_id
          KeyType: HASH

Outputs:
  ApiEndpoint:
    Value: !Sub 'https://${ClaimFastApi}.execute-api.${AWS::Region}.amazonaws.com/prod'
```

### Step 2: Deploy to Lambda

```bash
# Build
sam build

# Deploy (interactive)
sam deploy --guided

# Or deploy directly
sam deploy \
  --template-file template.yaml \
  --stack-name claimfast-stack \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides VertexAiProjectId=your_project_id \
  --region us-east-1
```

---

## Environment Configuration

### Development (.env.development)

```env
DEPLOYMENT_ENV=development
DEBUG=true
LANGCHAIN_VERBOSE=false
LOG_LEVEL=DEBUG
USE_MOCK_VISION_API=true
USE_MOCK_FRAUD_DB=true
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

### Staging (.env.staging)

```env
DEPLOYMENT_ENV=staging
DEBUG=false
LANGCHAIN_VERBOSE=false
LOG_LEVEL=INFO
USE_MOCK_VISION_API=false
USE_MOCK_FRAUD_DB=true
CORS_ORIGINS=["https://staging.claimfast.com"]
VERTEX_AI_PROJECT_ID=your_staging_project_id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash-002
DATABASE_URL=postgresql://user:pass@db.staging.rds.amazonaws.com/claimfast
```

### Production (.env.production)

```env
DEPLOYMENT_ENV=production
DEBUG=false
LANGCHAIN_DEBUG=false
LOG_LEVEL=WARNING
USE_MOCK_VISION_API=false
USE_MOCK_FRAUD_DB=false
CORS_ORIGINS=["https://claimfast.com"]
VERTEX_AI_PROJECT_ID=your_production_project_id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-flash-002
DATABASE_URL=postgresql://user:pass@db.prod.rds.amazonaws.com/claimfast
```

---

## Production Deployment

### Using Kubernetes (EKS)

#### 1. Create Helm Chart

```bash
helm create claimfast
```

#### 2. Deploy to EKS

```bash
# Create cluster
eksctl create cluster --name claimfast --region us-east-1

# Deploy
helm install claimfast ./claimfast \
  --set image.tag=v1.0.0 \
  --set vertexAiProjectId=$VERTEX_AI_PROJECT_ID \
  --set vertexAiLocation=$VERTEX_AI_LOCATION \
  --namespace production
```

### Infrastructure as Code (Terraform)

```hcl
# main.tf

provider "aws" {
  region = "us-east-1"
}

# ECS Cluster
resource "aws_ecs_cluster" "claimfast" {
  name = "claimfast-cluster"
}

# RDS PostgreSQL
resource "aws_db_instance" "claimfast" {
  identifier     = "claimfast-db"
  engine         = "postgres"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  skip_final_snapshot = true
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "claimfast" {
  cluster_id           = "claimfast-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

# CloudFront CDN for frontend
resource "aws_cloudfront_distribution" "claimfast" {
  # ... configuration
}
```

---

## Monitoring & Logging

### CloudWatch Dashboard

```python
# Setup CloudWatch monitoring
import boto3

cloudwatch = boto3.client('cloudwatch')

# Custom metric: Processing time
cloudwatch.put_metric_data(
    Namespace='ClaimFast',
    MetricData=[
        {
            'MetricName': 'ProcessingTime',
            'Value': 25.5,
            'Unit': 'Seconds'
        }
    ]
)
```

### Structured Logging

```python
# backend/config/logging_config.py

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }
    }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Vision API Connection Error

```
Error: Could not reach Vertex AI Gemini
Error: Could not reach Vertex AI Gemini
```

**Solution:**
- Verify VERTEX_AI_PROJECT_ID and Google credentials are set correctly
- Check internet connectivity
- Use USE_MOCK_VISION_API=true for testing

#### 2. Claim Processing Timeout

```
Error: Processing exceeded 60-second limit
```

**Solution:**
- Check Vertex AI response times
- Reduce image resolution
- Increase Lambda timeout to 120 seconds

#### 3. CORS Errors in Frontend

```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
- Update CORS_ORIGINS in backend config
- Verify frontend URL is in allowed origins

#### 4. Database Connection Failed

```
Error: Failed to connect to database
```

**Solution:**
- Verify DATABASE_URL format
- Check network connectivity to RDS
- Verify security group rules

### Debug Mode

Enable detailed logging:

```bash
export LANGCHAIN_DEBUG=true
export LOG_LEVEL=DEBUG
python -m pdb main.py
```

---

## Performance Tuning

### API Optimization

```python
# Add caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_policy(policy_id: str):
    # Cached policy retrieval
    pass
```

### Database Optimization

```sql
-- Index on policy_id for faster lookups
CREATE INDEX idx_policies_policy_id ON policies(policy_id);

-- Index on claim_id for status queries
CREATE INDEX idx_claims_claim_id ON claims(claim_id);
```

### Async Processing

```python
# Use async/await for I/O operations
async def analyze_damage_batch(claim_ids: List[str]):
    tasks = [analyze_damages(cid) for cid in claim_ids]
    return await asyncio.gather(*tasks)
```

---

## Support & Maintenance

- **Documentation**: `docs/` folder
- **Issue Tracking**: GitHub Issues
- **Email Support**: support@claimfast.com
- **SLA**: 99.9% uptime guarantee

