"""
Configuration settings for ClaimFast system.
Supports environment-based configuration for different deployment stages.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class Config:
    """Base configuration"""
    
    # API Configuration
    API_TITLE = "ClaimFast - Insurance FNOL System"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "Automated First Notice of Loss processing"
    
    # Vertex AI Configuration
    VERTEX_AI_PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID", "")
    VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    VERTEX_AI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash-002")
    
    # LangChain Configuration
    LANGCHAIN_VERBOSE = os.getenv("LANGCHAIN_VERBOSE", "false").lower() == "true"
    LANGCHAIN_DEBUG = os.getenv("LANGCHAIN_DEBUG", "false").lower() == "true"
    
    # Fraud Detection Thresholds
    FRAUD_RISK_THRESHOLD = 60  # Score above this triggers manual review
    FRAUD_CRITICAL_THRESHOLD = 80  # Score above this triggers rejection
    
    # Processing Configuration
    MAX_PROCESSING_TIME_SECONDS = 60
    IMAGE_ANALYSIS_TIMEOUT = 30
    
    # Database Configuration (can be extended)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claimfast.db")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Deployment Configuration
    DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "development")  # development, staging, production
    
    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5000",
    ]
    
    # Agent Timeout Configurations (seconds)
    AGENT_TIMEOUTS = {
        "intake": 10,
        "damage_assessment": 30,
        "policy": 15,
        "fraud_detection": 20,
        "decision": 10,
        "explainability": 10,
    }
    
    # Damage Severity Thresholds (0-100)
    SEVERITY_THRESHOLDS = {
        "low": (0, 30),
        "medium": (31, 70),
        "high": (71, 100),
    }
    
    # Policy Deductible Defaults (in INR)
    DEFAULT_DEDUCTIBLES = {
        "motor": 10000,
        "health": 5000,
        "property": 50000,
    }
    
    # Demo/Mock Configuration
    USE_MOCK_VISION_API = os.getenv("USE_MOCK_VISION_API", "true").lower() == "true"
    USE_MOCK_FRAUD_DB = os.getenv("USE_MOCK_FRAUD_DB", "true").lower() == "true"


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False
    USE_MOCK_VISION_API = True
    USE_MOCK_FRAUD_DB = True


class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = False
    TESTING = True
    USE_MOCK_VISION_API = True
    USE_MOCK_FRAUD_DB = True
    DATABASE_URL = "sqlite:///./test.db"


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    USE_MOCK_VISION_API = False
    USE_MOCK_FRAUD_DB = False


def get_config():
    """Get appropriate configuration based on environment"""
    env = os.getenv("DEPLOYMENT_ENV", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    
    return config_map.get(env, DevelopmentConfig)()


# Export active config
config = get_config()
