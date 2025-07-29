"""
Configuration settings for the Anonymous Telegram Bot
"""

import os

class Config:
    """Base configuration class"""
    
    # Bot settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'anonymous_bot_secret_key_2025')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Server settings
    HOST = '0.0.0.0'
    BOT_PORT = 8000
    WEB_PORT = 5000
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Anonymous ID settings
    ANON_ID_LENGTH = 8
    ANON_ID_PREFIX = 'anon_'
    
    # Message limits
    MAX_MESSAGE_LENGTH = 4096  # Telegram's message limit
    MAX_CONVERSATIONS = 1000   # Memory limit for conversations
    
    # Auto-cleanup settings (in seconds)
    CONVERSATION_TIMEOUT = 7 * 24 * 3600  # 7 days
    CLEANUP_INTERVAL = 3600  # 1 hour
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        if not cls.ADMIN_CHAT_ID:
            raise ValueError("ADMIN_CHAT_ID environment variable is required")
        
        try:
            int(cls.ADMIN_CHAT_ID)
        except ValueError:
            raise ValueError("ADMIN_CHAT_ID must be a valid integer")
        
        return True

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'INFO'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}

def get_config(config_name=None):
    """Get configuration based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config.get(config_name, Config)
