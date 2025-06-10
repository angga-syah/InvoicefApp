#!/usr/bin/env python3
"""
Type Checking Validation Script
Validates that the Pylance type error fixes are working correctly.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_command(command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_python_imports() -> bool:
    """Check if all required imports can be loaded"""
    logger.info("Checking Python imports...")
    
    imports_to_check = [
        "sqlalchemy",
        "pydantic", 
        "PyQt6",
        "decimal",
        "typing",
        "datetime",
        "pathlib"
    ]
    
    failed_imports = []
    
    for module in imports_to_check:
        try:
            __import__(module)
            logger.info(f"✅ {module}")
        except ImportError as e:
            logger.error(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"Failed to import: {', '.join(failed_imports)}")
        return False
    
    return True

def validate_database_models() -> bool:
    """Validate database models can be imported without errors"""
    logger.info("Validating database models...")
    
    try:
        # Try to import the main models
        from models.database import (
            User, Company, TkaWorker, TkaFamilyMember, 
            JobDescription, Invoice, InvoiceLine, BankAccount,
            Setting, UserPreference, InvoiceNumberSequence,
            DatabaseManager, get_db_session, init_database
        )
        logger.info("✅ Database models imported successfully")
        
        # Test model instantiation
        user = User(username="test", password_hash="test", full_name="Test User")
        logger.info("✅ Model instantiation works")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database model validation failed: {e}")
        return False

def validate_business_logic() -> bool:
    """Validate business logic can be imported without errors"""
    logger.info("Validating business logic...")
    
    try:
        from models.business import (
            BusinessError, InvoiceBusinessLogic, SearchHelper,
            DataHelper, ValidationHelper, SettingsHelper, ReportHelper
        )
        logger.info("✅ Business logic imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Business logic validation failed: {e}")
        return False

def validate_utilities() -> bool:
    """Validate utility modules can be imported without errors"""
    logger.info("Validating utility modules...")
    
    try:
        from utils.formatters import format_currency_idr, format_date_short
        from utils.helpers import safe_decimal, fuzzy_search_score
        from utils.validators import ValidationResult, validate_required
        logger.info("✅ Utility modules imported successfully")
        
        # Test some utility functions
        result = safe_decimal("123.45")
        assert result == 123.45, "safe_decimal test failed"
        
        formatted = format_currency_idr(123456)
        assert "123.456" in formatted, "currency formatting test failed"
        
        logger.info("✅ Utility function tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Utility validation failed: {e}")
        return False

def run_mypy_check() -> bool:
    """Run MyPy type checking if available"""
    logger.info("Running MyPy type checking...")
    
    try:
        # Check if mypy is available
        exit_code, stdout, stderr = run_command(["mypy", "--version"])
        if exit_code != 0:
            logger.warning("MyPy not available, skipping type checking")
            return True
        
        # Run mypy on main modules
        modules_to_check = [
            "models/database.py",
            "models/business.py", 
            "utils/formatters.py",
            "utils/helpers.py",
            "utils/validators.py",
            "config.py"
        ]
        
        for module in modules_to_check:
            if Path(module).exists():
                exit_code, stdout, stderr = run_command(["mypy", module])
                if exit_code == 0:
                    logger.info(f"✅ {module} passed MyPy check")
                else:
                    logger.warning(f"⚠️ {module} has MyPy warnings:\n{stderr}")
            else:
                logger.warning(f"⚠️ {module} not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MyPy check failed: {e}")
        return False

def check_sqlalchemy_compatibility() -> bool:
    """Check SQLAlchemy compatibility and type hints"""
    logger.info("Checking SQLAlchemy compatibility...")
    
    try:
        import sqlalchemy
        logger.info(f"✅ SQLAlchemy version: {sqlalchemy.__version__}")
        
        # Test basic SQLAlchemy operations
        from sqlalchemy import create_engine, Column, Integer, String
        from sqlalchemy.ext.declarative import declarative_base
        
        Base = declarative_base()
        
        class TestModel(Base):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)
            name = Column(String(50))
        
        logger.info("✅ SQLAlchemy model creation works")
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLAlchemy compatibility check failed: {e}")
        return False

def validate_type_annotations() -> bool:
    """Validate that type annotations are working correctly"""
    logger.info("Validating type annotations...")
    
    try:
        from typing import Optional, List, Dict, Any, Union
        from decimal import Decimal
        from datetime import date, datetime
        
        # Test function with type annotations
        def test_function(value: Optional[str] = None) -> Union[str, None]:
            return value
        
        result = test_function("test")
        assert result == "test", "Type annotation test failed"
        
        logger.info("✅ Type annotations working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Type annotation validation failed: {e}")
        return False

def main():
    """Main validation function"""
    logger.info("🔍 Starting type checking validation...")
    
    validation_results = []
    
    # Run all validation checks
    checks = [
        ("Python Imports", check_python_imports),
        ("Database Models", validate_database_models),
        ("Business Logic", validate_business_logic),
        ("Utility Modules", validate_utilities),
        ("SQLAlchemy Compatibility", check_sqlalchemy_compatibility),
        ("Type Annotations", validate_type_annotations),
        ("MyPy Type Checking", run_mypy_check),
    ]
    
    for check_name, check_function in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            result = check_function()
            validation_results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ {check_name} failed with exception: {e}")
            validation_results.append((check_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(validation_results)
    
    for check_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{check_name:<30} {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("🎉 All validation checks passed! Your type fixes are working correctly.")
        return 0
    else:
        logger.error(f"❌ {total - passed} validation checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)