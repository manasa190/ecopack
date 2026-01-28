import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:manu262004@localhost:5432/ecopackai"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "ecopackai-secure-key-2024")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"

    # JWT configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = "HS256"
    
    # Security headers
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = True