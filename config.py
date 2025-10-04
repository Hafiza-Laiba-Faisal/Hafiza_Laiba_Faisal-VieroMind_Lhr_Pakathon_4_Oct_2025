"""
Configuration settings for NeuroShield
"""

import os
from datetime import timedelta


class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    DEBUG = False
    TESTING = False

    # Database
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'neuroshield.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'npy', 'csv', 'edf', 'mat'}

    # Model paths
    MODEL_PATH = 'models/eeg_classifier.pkl'
    SCALER_PATH = 'models/scaler.pkl'

    # EEG settings
    SAMPLING_FREQUENCY = 250  # Hz
    N_CHANNELS = 19
    EPOCH_LENGTH = 500  # samples (2 seconds at 250 Hz)

    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Security
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CORS settings
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000']

    # ML Model settings
    MODEL_CONFIDENCE_THRESHOLD = 0.7
    RISK_SCORE_THRESHOLD = 0.6

    # NLP Coach settings
    COACH_MAX_HISTORY = 100  # Maximum chat history to load
    COACH_RESPONSE_DELAY = 0.5  # seconds

    # Analytics
    ANALYTICS_RETENTION_DAYS = 90  # days to keep detailed analytics

    # Feature flags
    ENABLE_REAL_EEG = False  # Enable real EEG device integration
    ENABLE_ADVANCED_NLP = False  # Enable transformer-based NLP
    ENABLE_RESEARCH_MODE = True  # Allow opt-in data sharing for research


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Override with environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'neuroshield_prod.db'


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_PATH = ':memory:'  # In-memory database for tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])