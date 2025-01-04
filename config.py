# config.py

import os


class BaseConfig:
    DEBUG = False
    TESTING = False
    # Rate limit settings can be configured per environment
    # Defaulting to 100 requests per hour for demonstration
    RATE_LIMITS = ["100/hour"]


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    RATE_LIMITS = ["200/hour"]  # Higher limit for development


class StagingConfig(BaseConfig):
    DEBUG = True
    RATE_LIMITS = ["50/hour"]  # More restrictive rate limits in staging


class ProductionConfig(BaseConfig):
    RATE_LIMITS = ["20/hour"]  # Example production rate limits


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    elif env == "staging":
        return StagingConfig
    else:
        return DevelopmentConfig
