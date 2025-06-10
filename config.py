"""
Invoice Management System - Configuration Management
Handles application configuration from environment variables and provides
centralized configuration access throughout the application.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import logging

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="invoice_management", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="", description="Database password")
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=30, description="Max pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout")
    pool_recycle: int = Field(default=3600, description="Pool recycle time")
    
    model_config = {"env_prefix": "DB_"}
    
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
    
    name: str = Field(default="Invoice Management System", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(default="change-this-secret-key", description="Secret key")
    session_timeout: int = Field(default=3600, description="Session timeout")
    
    # Business configuration
    default_vat_percentage: float = Field(default=11.00, description="Default VAT percentage")
    invoice_number_format: str = Field(default="INV-{YY}-{MM}-{NNN}", description="Invoice number format")
    company_tagline: str = Field(default="Spirit of Services", description="Company tagline")
    default_currency: str = Field(default="IDR", description="Default currency")
    
    # Office information
    office_address_line1: str = Field(default="Jakarta Office", description="Office address line 1")
    office_address_line2: str = Field(default="Indonesia", description="Office address line 2")
    office_phone: str = Field(default="+62-21-XXXXXXX", description="Office phone")
    office_email: str = Field(default="info@company.com", description="Office email")

    model_config = {"env_prefix": "APP_"}

class UIConfig(BaseSettings):
    """User interface configuration"""
    
    default_theme: str = Field(default="light", description="Default theme")
    animation_duration: int = Field(default=200, description="Animation duration")
    window_remember_geometry: bool = Field(default=True, description="Remember window geometry")
    high_dpi_scaling: bool = Field(default=True, description="High DPI scaling")
    default_font: str = Field(default="Segoe UI", description="Default font")
    default_font_size: int = Field(default=9, description="Default font size")
    
    model_config = {"env_prefix": "UI_"}
    
    @field_validator('default_theme')
    @classmethod
    def validate_theme(cls, v):
        valid_themes = ['light', 'dark']
        if v not in valid_themes:
            raise ValueError(f"Theme must be one of {valid_themes}")
        return v

class PerformanceConfig(BaseSettings):
    """Performance optimization configuration"""
    
    cache_size: int = Field(default=1000, description="Cache size")
    search_debounce_ms: int = Field(default=300, description="Search debounce milliseconds")
    max_search_results: int = Field(default=50, description="Max search results")
    auto_save_interval: int = Field(default=30, description="Auto save interval")
    backup_interval: int = Field(default=3600, description="Backup interval")

    model_config = {"env_prefix": "PERF_"}

class RedisConfig(BaseSettings):
    """Redis cache configuration"""
    
    enabled: bool = Field(default=False, description="Redis enabled")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database")
    password: Optional[str] = Field(default=None, description="Redis password")
    
    model_config = {"env_prefix": "REDIS_"}
    
    @property
    def url(self) -> str:
        """Get Redis connection URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

class LoggingConfig(BaseSettings):
    """Logging configuration"""
    
    level: str = Field(default="INFO", description="Log level")
    file_max_size: int = Field(default=10485760, description="Log file max size")  # 10MB
    file_backup_count: int = Field(default=5, description="Log file backup count")
    to_console: bool = Field(default=True, description="Log to console")
    to_file: bool = Field(default=True, description="Log to file")
    
    model_config = {"env_prefix": "LOG_"}
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

class SecurityConfig(BaseSettings):
    """Security configuration"""
    
    password_min_length: int = Field(default=8, description="Password min length")
    password_require_special_chars: bool = Field(default=True, description="Password require special chars")
    remember_login: bool = Field(default=True, description="Remember login")
    max_login_attempts: int = Field(default=5, description="Max login attempts")
    lockout_duration: int = Field(default=300, description="Lockout duration")

    model_config = {"env_prefix": "SEC_"}

class ExportConfig(BaseSettings):
    """Export and printing configuration"""
    
    export_directory: str = Field(default="./exports", description="Export directory")
    pdf_compression: bool = Field(default=True, description="PDF compression")
    pdf_quality: str = Field(default="high", description="PDF quality")
    paper_size: str = Field(default="letter", description="Paper size")
    print_margins: int = Field(default=20, description="Print margins")
    excel_include_formulas: bool = Field(default=True, description="Excel include formulas")

    model_config = {"env_prefix": "EXPORT_"}

class BackupConfig(BaseSettings):
    """Backup configuration"""
    
    enabled: bool = Field(default=True, description="Backup enabled")
    directory: str = Field(default="./backups", description="Backup directory")
    retention_days: int = Field(default=30, description="Backup retention days")
    auto_backup_enabled: bool = Field(default=True, description="Auto backup enabled")

    model_config = {"env_prefix": "BACKUP_"}

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