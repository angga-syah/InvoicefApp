#!/usr/bin/env python3
"""
Invoice Management System - Application Entry Point
Main entry point for the Invoice Management System application.
Handles initialization, error handling, and application lifecycle.
"""

import sys
import os
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor

# Application imports
from config import get_config, validate_configuration, app_config, ui_config
from models.database import db_manager, init_database
from ui.main_window import MainWindow
from services.cache_service import warm_up_cache, cleanup_cache
from utils.helpers import ensure_directory

# Setup logging
def setup_logging():
    """Setup application logging"""
    try:
        # Ensure logs directory exists
        ensure_directory("logs")
        
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = Path("logs") / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info("Logging system initialized")
        return True
        
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        return False

class InitializationThread(QThread):
    """Background thread for application initialization"""
    
    progress_updated = pyqtSignal(str, int)
    initialization_completed = pyqtSignal(bool, str)
    
    def run(self):
        """Run initialization process"""
        try:
            # Step 1: Validate configuration
            self.progress_updated.emit("Validating configuration...", 10)
            validate_configuration()
            
            # Step 2: Test database connection
            self.progress_updated.emit("Testing database connection...", 30)
            if not db_manager.test_connection():
                raise Exception("Database connection failed")
            
            # Step 3: Initialize database schema
            self.progress_updated.emit("Initializing database...", 50)
            init_database()
            
            # Step 4: Warm up cache
            self.progress_updated.emit("Warming up cache...", 70)
            warm_up_cache()
            
            # Step 5: Load application settings
            self.progress_updated.emit("Loading application settings...", 90)
            # Additional initialization can go here
            
            self.progress_updated.emit("Ready!", 100)
            self.initialization_completed.emit(True, "Initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Initialization failed: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.initialization_completed.emit(False, error_msg)

class SplashScreen(QSplashScreen):
    """Custom splash screen with progress indication"""
    
    def __init__(self):
        # Create a simple splash screen pixmap
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(255, 255, 255))
        
        # Draw on pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background gradient
        from PyQt6.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 0, 300)
        gradient.setColorAt(0, QColor(0, 123, 255))
        gradient.setColorAt(1, QColor(0, 86, 179))
        painter.fillRect(pixmap.rect(), gradient)
        
        # App name
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, app_config.name)
        
        # Tagline
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(50, 250, app_config.company_tagline)
        
        painter.end()
        
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        
        # Progress label
        self.progress_text = "Initializing..."
        
    def showMessage(self, message: str, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, color=QColor(255, 255, 255)):
        """Show message on splash screen"""
        self.progress_text = message
        super().showMessage(message, alignment, color)
        QApplication.processEvents()

class InvoiceApplication(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.main_window = None
        self.splash = None
        self.init_thread = None
        
        # Set application properties
        self.setApplicationName(app_config.name)
        self.setApplicationVersion(app_config.version)
        self.setOrganizationName("Invoice Management System")
        
        # Setup application
        self._setup_application()
    
    def _setup_application(self):
        """Setup application properties and style"""
        try:
            # High DPI support
            if ui_config.high_dpi_scaling:
                self.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
                self.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            
            # Set default font
            font = QFont(ui_config.default_font, ui_config.default_font_size)
            self.setFont(font)
            
            # Load stylesheet
            self._load_stylesheet()
            
            logging.info("Application setup completed")
            
        except Exception as e:
            logging.error(f"Error in application setup: {e}")
    
    def _load_stylesheet(self):
        """Load application stylesheet"""
        try:
            style_file = Path("ui") / "styles.qss"
            if style_file.exists():
                with open(style_file, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                logging.info("Stylesheet loaded successfully")
            else:
                logging.warning("Stylesheet file not found, using default styling")
        except Exception as e:
            logging.error(f"Error loading stylesheet: {e}")
    
    def initialize(self):
        """Initialize application with splash screen"""
        try:
            # Show splash screen
            self.splash = SplashScreen()
            self.splash.show()
            self.splash.showMessage("Starting application...")
            
            # Start initialization thread
            self.init_thread = InitializationThread()
            self.init_thread.progress_updated.connect(self._update_splash)
            self.init_thread.initialization_completed.connect(self._initialization_completed)
            self.init_thread.start()
            
        except Exception as e:
            logging.error(f"Error during initialization: {e}")
            self._show_error("Initialization Error", f"Failed to initialize application: {e}")
            return False
        
        return True
    
    def _update_splash(self, message: str, progress: int):
        """Update splash screen with progress"""
        if self.splash:
            self.splash.showMessage(f"{message} ({progress}%)")
    
    def _initialization_completed(self, success: bool, message: str):
        """Handle initialization completion"""
        try:
            if success:
                # Hide splash and show main window
                if self.splash:
                    self.splash.close()
                
                # Create and show main window
                self.main_window = MainWindow()
                self.main_window.show()
                
                logging.info("Application started successfully")
                
            else:
                # Show error and exit
                if self.splash:
                    self.splash.close()
                
                self._show_error("Initialization Failed", message)
                self.quit()
                
        except Exception as e:
            logging.error(f"Error in initialization completion: {e}")
            self._show_error("Application Error", f"Failed to start application: {e}")
            self.quit()
    
    def _show_error(self, title: str, message: str):
        """Show error message"""
        QMessageBox.critical(None, title, message)
    
    def excepthook(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle Ctrl+C gracefully
            logging.info("Application interrupted by user")
            self.quit()
            return
        
        # Log the exception
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical(f"Uncaught exception: {error_msg}")
        
        # Show error dialog
        QMessageBox.critical(
            None, 
            "Critical Error", 
            f"An unexpected error occurred:\n\n{exc_value}\n\nPlease check the log file for details."
        )
        
        # Exit application
        self.quit()

def check_system_requirements():
    """Check system requirements"""
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        errors.append("Python 3.8 or higher is required")
    
    # Check required modules
    required_modules = [
        'PyQt6', 'sqlalchemy', 'psycopg2', 'reportlab', 
        'openpyxl', 'python-dotenv', 'bcrypt'
    ]
    
    for module in required_modules:
        try:
            __import__(module.replace('-', '_'))
        except ImportError:
            errors.append(f"Required module '{module}' is not installed")
    
    # Check write permissions
    try:
        test_file = Path("logs") / "test_write.tmp"
        ensure_directory("logs")
        test_file.write_text("test")
        test_file.unlink()
    except Exception:
        errors.append("No write permission in application directory")
    
    return errors

def main():
    """Main entry point"""
    print(f"Starting {app_config.name} v{app_config.version}")
    print("=" * 50)
    
    # Check system requirements
    print("Checking system requirements...")
    requirements_errors = check_system_requirements()
    if requirements_errors:
        print("❌ System requirements check failed:")
        for error in requirements_errors:
            print(f"  - {error}")
        print("\nPlease install missing requirements and try again.")
        return 1
    
    print("✅ System requirements check passed")
    
    # Setup logging
    print("Setting up logging...")
    if not setup_logging():
        print("❌ Failed to setup logging")
        return 1
    
    print("✅ Logging setup completed")
    
    # Initialize configuration
    print("Loading configuration...")
    try:
        config = get_config()
        print(f"✅ Configuration loaded (Debug: {config.app.debug})")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1
    
    # Create application
    try:
        print("Creating application...")
        app = InvoiceApplication(sys.argv)
        
        # Install exception handler
        sys.excepthook = app.excepthook
        
        print("✅ Application created")
        
        # Initialize application
        print("Initializing application...")
        if not app.initialize():
            print("❌ Application initialization failed")
            return 1
        
        # Run application
        print("🚀 Starting application...")
        exit_code = app.exec()
        
        # Cleanup
        print("Cleaning up...")
        cleanup_cache()
        
        print(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted by user")
        return 130

if __name__ == "__main__":
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Run main function
    exit_code = main()
    sys.exit(exit_code)