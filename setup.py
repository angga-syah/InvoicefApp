#!/usr/bin/env python3
"""
Invoice Management System - Setup and Installation Script
Setup script for packaging and distributing the Invoice Management System.
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# Read version from config
def get_version():
    """Get version from config file"""
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        from config import app_config
        return app_config.version
    except ImportError:
        return "1.0.0"

# Read README file
def get_long_description():
    """Get long description from README file"""
    readme_file = Path(__file__).parent / "README.md"
    if readme_file.exists():
        with open(readme_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# Read requirements
def get_requirements():
    """Get requirements from requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    if requirements_file.exists():
        with open(requirements_file, "r", encoding="utf-8") as f:
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Remove version pinning for setup.py
                    package = line.split("==")[0].split(">=")[0].split("<=")[0]
                    requirements.append(package)
            return requirements
    return []

# Development requirements
dev_requirements = [
    "pytest>=7.4.0",
    "pytest-qt>=4.2.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=1.3.0",
    "coverage>=7.3.0",
    "pre-commit>=3.4.0",
]

setup(
    # Basic package information
    name="invoice-management-system",
    version=get_version(),
    description="Professional Invoice Management System for TKA Services",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="Invoice Management System Team",
    author_email="admin@invoice-system.com",
    url="https://github.com/your-org/invoice-management-system",
    
    # Package configuration
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    package_data={
        "ui": ["*.qss"],
        "assets": ["icons/*", "templates/*"],
        "": ["*.sql", "*.env.example"],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=get_requirements(),
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=7.4.0",
            "pytest-qt>=4.2.0",
            "coverage>=7.3.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Entry points
    entry_points={
        "console_scripts": [
            "invoice-manager=main:main",
        ],
        "gui_scripts": [
            "invoice-manager-gui=main:main",
        ],
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "Environment :: X11 Applications :: Qt",
    ],
    
    # Keywords
    keywords="invoice management accounting business TKA services",
    
    # License
    license="MIT",
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/your-org/invoice-management-system/issues",
        "Source": "https://github.com/your-org/invoice-management-system",
        "Documentation": "https://invoice-management-system.readthedocs.io/",
    },
    
    # ZIP safe
    zip_safe=False,
)

# Custom commands
class CustomCommands:
    """Custom setup commands"""
    
    @staticmethod
    def create_desktop_entry():
        """Create desktop entry for Linux systems"""
        if sys.platform.startswith('linux'):
            desktop_entry = """[Desktop Entry]
Name=Invoice Management System
Comment=Professional Invoice Management System for TKA Services
Exec=invoice-manager-gui
Icon=invoice-manager
Terminal=false
Type=Application
Categories=Office;Finance;
"""
            try:
                desktop_dir = Path.home() / ".local/share/applications"
                desktop_dir.mkdir(parents=True, exist_ok=True)
                
                desktop_file = desktop_dir / "invoice-manager.desktop"
                desktop_file.write_text(desktop_entry)
                
                print(f"✅ Desktop entry created: {desktop_file}")
            except Exception as e:
                print(f"⚠️  Failed to create desktop entry: {e}")
    
    @staticmethod
    def setup_database():
        """Setup database schema"""
        try:
            from models.database import init_database
            init_database()
            print("✅ Database schema initialized")
        except Exception as e:
            print(f"⚠️  Database setup failed: {e}")
            print("You can run database setup manually later")
    
    @staticmethod
    def create_sample_config():
        """Create sample configuration files"""
        try:
            # Create .env.example
            env_example = Path(".env.example")
            if not env_example.exists():
                env_content = """# Invoice Management System - Configuration Template
# Copy this file to .env and modify the values

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=invoice_management
DB_USER=postgres
DB_PASSWORD=your_password_here

# Application Configuration
APP_NAME=Invoice Management System
DEBUG_MODE=False
SECRET_KEY=change-this-secret-key

# UI Configuration
DEFAULT_THEME=light
HIGH_DPI_SCALING=True

# Business Configuration
DEFAULT_VAT_PERCENTAGE=11.00
COMPANY_TAGLINE=Spirit of Services
"""
                env_example.write_text(env_content)
                print(f"✅ Sample configuration created: {env_example}")
            
        except Exception as e:
            print(f"⚠️  Failed to create sample configuration: {e}")

def post_install():
    """Post-installation tasks"""
    print("\n" + "="*50)
    print("Invoice Management System - Post-Installation Setup")
    print("="*50)
    
    commands = CustomCommands()
    
    # Create sample config
    commands.create_sample_config()
    
    # Create desktop entry (Linux only)
    commands.create_desktop_entry()
    
    # Setup database (optional)
    setup_db = input("\nSetup database now? (y/N): ").lower().strip()
    if setup_db == 'y':
        commands.setup_database()
    
    print("\n" + "="*50)
    print("Installation completed!")
    print("="*50)
    print("\nNext steps:")
    print("1. Copy .env.example to .env and configure your settings")
    print("2. Setup PostgreSQL database")
    print("3. Run: invoice-manager-gui")
    print("\nFor more information, see README.md")
    print("="*50)

if __name__ == "__main__":
    # Check if this is a post-install run
    if len(sys.argv) > 1 and sys.argv[1] == "post_install":
        post_install()
    else:
        # Normal setup
        setup()
        
        # Run post-install if installing
        if "install" in sys.argv:
            post_install()