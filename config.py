"""
Invoice Management System - Configuration Management
Handles application configuration from environment variables and provides
centralized configuration access throughout the application.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseSettings, Field, validator
import logging

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="invoice_management", env="DB_NAME")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    @property
    def url(self) -> str:
        """Get SQLAlchemy database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_url(self) -> str:
        """Get async SQLAlchemy database URL"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

class AppConfig(BaseSettings):
    """Main application configuration"""
    
    name: str = Field(default="Invoice Management System", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG_MODE")
    secret_key: str = Field(default="change-this-secret-key", env="SECRET_KEY")
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")
    
    # Business configuration
    default_vat_percentage: float = Field(default=11.00, env="DEFAULT_VAT_PERCENTAGE")
    invoice_number_format: str = Field(default="INV-{YY}-{MM}-{NNN}", env="INVOICE_NUMBER_FORMAT")
    company_tagline: str = Field(default="Spirit of Services", env="COMPANY_TAGLINE")
    default_currency: str = Field(default="IDR", env="DEFAULT_CURRENCY")
    
    # Office information
    office_address_line1: str = Field(default="Jakarta Office", env="OFFICE_ADDRESS_LINE1")
    office_address_line2: str = Field(default="Indonesia", env="OFFICE_ADDRESS_LINE2")
    office_phone: str = Field(default="+62-21-XXXXXXX", env="OFFICE_PHONE")
    office_email: str = Field(default="info@company.com", env="OFFICE_EMAIL")

class UIConfig(BaseSettings):
    """User interface configuration"""
    
    default_theme: str = Field(default="light", env="DEFAULT_THEME")
    animation_duration: int = Field(default=200, env="ANIMATION_DURATION")
    window_remember_geometry: bool = Field(default=True, env="WINDOW_REMEMBER_GEOMETRY")
    high_dpi_scaling: bool = Field(default=True, env="HIGH_DPI_SCALING")
    default_font: str = Field(default="Segoe UI", env="DEFAULT_FONT")
    default_font_size: int = Field(default=9, env="DEFAULT_FONT_SIZE")
    
    @validator('default_theme')
    def validate_theme(cls, v):
        valid_themes = ['light', 'dark']
        if v not in valid_themes:
            raise ValueError(f"Theme must be one of {valid_themes}")
        return v

class PerformanceConfig(BaseSettings):
    """Performance optimization configuration"""
    
    cache_size: int = Field(default=1000, env="CACHE_SIZE")
    search_debounce_ms: int = Field(default=300, env="SEARCH_DEBOUNCE_MS")
    max_search_results: int = Field(default=50, env="MAX_SEARCH_RESULTS")
    auto_save_interval: int = Field(default=30, env="AUTO_SAVE_INTERVAL")
    backup_interval: int = Field(default=3600, env="BACKUP_INTERVAL")

class RedisConfig(BaseSettings):
    """Redis cache configuration"""
    
    enabled: bool = Field(default=False, env="REDIS_ENABLED")
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    @property
    def url(self) -> str:
        """Get Redis connection URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

class LoggingConfig(BaseSettings):
    """Logging configuration"""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    file_max_size: int = Field(default=10485760, env="LOG_FILE_MAX_SIZE")  # 10MB
    file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    to_console: bool = Field(default=True, env="LOG_TO_CONSOLE")
    to_file: bool = Field(default=True, env="LOG_TO_FILE")
    
    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

class SecurityConfig(BaseSettings):
    """Security configuration"""
    
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_special_chars: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL_CHARS")
    remember_login: bool = Field(default=True, env="REMEMBER_LOGIN")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration: int = Field(default=300, env="LOCKOUT_DURATION")

class ExportConfig(BaseSettings):
    """Export and printing configuration"""
    
    export_directory: str = Field(default="./exports", env="EXPORT_DIRECTORY")
    pdf_compression: bool = Field(default=True, env="PDF_COMPRESSION")
    pdf_quality: str = Field(default="high", env="PDF_QUALITY")
    paper_size: str = Field(default="letter", env="PAPER_SIZE")
    print_margins: int = Field(default=20, env="PRINT_MARGINS")
    excel_include_formulas: bool = Field(default=True, env="EXCEL_INCLUDE_FORMULAS")

class BackupConfig(BaseSettings):
    """Backup configuration"""
    
    enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    directory: str = Field(default="./backups", env="BACKUP_DIRECTORY")
    retention_days: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    auto_backup_enabled: bool = Field(default=True, env="AUTO_BACKUP_ENABLED")

class Config:
    """Main configuration class that combines all configuration sections"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.app = AppConfig()
        self.ui = UIConfig()
        self.performance = PerformanceConfig()
        self.redis = RedisConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.export = ExportConfig()
        self.backup = BackupConfig()
        
        # Initialize directories
        self._initialize_directories()
        
        # Setup logging
        self._setup_logging()
    
    def _initialize_directories(self):
        """Create required directories if they don't exist"""
        directories = [
            Path("logs"),
            Path(self.export.export_directory),
            Path(self.backup.directory),
            Path("assets/icons"),
            Path("assets/templates")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """Setup application logging configuration"""
        log_level = getattr(logging, self.logging.level)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        if self.logging.to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.logging.to_file:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                'logs/app.log',
                maxBytes=self.logging.file_max_size,
                backupCount=self.logging.file_backup_count
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    @property
    def is_development(self) -> bool:
        """Check if application is running in development mode"""
        return self.app.debug
    
    @property
    def is_production(self) -> bool:
        """Check if application is running in production mode"""
        return not self.app.debug

# Global configuration instance
config = Config()

# Convenience exports
database_config = config.database
app_config = config.app
ui_config = config.ui
performance_config = config.performance
redis_config = config.redis
logging_config = config.logging
security_config = config.security
export_config = config.export
backup_config = config.backup

def get_config() -> Config:
    """Get global configuration instance"""
    return config

def validate_configuration():
    """Validate all configuration settings"""
    errors = []
    
    # Database validation
    if not database_config.password:
        errors.append("Database password is required")
    
    # Security validation
    if app_config.secret_key == "change-this-secret-key":
        errors.append("Secret key must be changed from default value")
    
    # Directory validation
    required_dirs = [
        export_config.export_directory,
        backup_config.directory
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory {directory}: {e}")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return True

if __name__ == "__main__":
    # Configuration validation
    try:
        validate_configuration()
        print("✅ Configuration validation passed")
        print(f"📍 Database URL: {database_config.url}")
        print(f"🎨 UI Theme: {ui_config.default_theme}")
        print(f"📊 Cache enabled: {redis_config.enabled}")
        print(f"🔧 Debug mode: {app_config.debug}")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        exit(1)