"""
Invoice Management System - Data Validation Functions
Comprehensive validation functions for all business entities and operations.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import logging

from utils.helpers import safe_decimal, clean_string

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)

class ValidationResult:
    """Result of validation operation"""
    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
    
    def add_error(self, message: str, field: str = None, code: str = None):
        """Add validation error"""
        self.is_valid = False
        self.errors.append({
            'message': message,
            'field': field,
            'code': code
        })
    
    def add_warning(self, message: str, field: str = None, code: str = None):
        """Add validation warning"""
        self.warnings.append({
            'message': message,
            'field': field,
            'code': code
        })
    
    def get_first_error(self) -> Optional[str]:
        """Get first error message"""
        return self.errors[0]['message'] if self.errors else None
    
    def get_errors_by_field(self, field: str) -> List[str]:
        """Get all errors for specific field"""
        return [error['message'] for error in self.errors if error['field'] == field]

# ========== BASIC VALIDATORS ==========

def validate_required(value: Any, field_name: str = "Field") -> ValidationResult:
    """Validate that field is not empty"""
    result = ValidationResult()
    
    if value is None or (isinstance(value, str) and not value.strip()):
        result.add_error(f"{field_name} is required", field_name.lower(), "required")
    
    return result

def validate_string_length(value: str, min_length: int = 0, max_length: int = None, 
                          field_name: str = "Field") -> ValidationResult:
    """Validate string length constraints"""
    result = ValidationResult()
    
    if not isinstance(value, str):
        result.add_error(f"{field_name} must be a string", field_name.lower(), "invalid_type")
        return result
    
    length = len(value.strip())
    
    if length < min_length:
        result.add_error(
            f"{field_name} must be at least {min_length} characters", 
            field_name.lower(), "too_short"
        )
    
    if max_length and length > max_length:
        result.add_error(
            f"{field_name} cannot exceed {max_length} characters", 
            field_name.lower(), "too_long"
        )
    
    return result

def validate_numeric_range(value: Any, min_value: Decimal = None, max_value: Decimal = None,
                          field_name: str = "Field") -> ValidationResult:
    """Validate numeric value within range"""
    result = ValidationResult()
    
    try:
        decimal_value = safe_decimal(value)
    except (ValueError, TypeError):
        result.add_error(f"{field_name} must be a valid number", field_name.lower(), "invalid_number")
        return result
    
    if min_value is not None and decimal_value < min_value:
        result.add_error(
            f"{field_name} must be at least {min_value}", 
            field_name.lower(), "too_small"
        )
    
    if max_value is not None and decimal_value > max_value:
        result.add_error(
            f"{field_name} cannot exceed {max_value}", 
            field_name.lower(), "too_large"
        )
    
    return result

def validate_positive_number(value: Any, field_name: str = "Field", 
                           allow_zero: bool = False) -> ValidationResult:
    """Validate that number is positive"""
    result = ValidationResult()
    
    try:
        decimal_value = safe_decimal(value)
        min_value = Decimal('0') if allow_zero else Decimal('0.01')
        
        if decimal_value < min_value:
            message = f"{field_name} must be positive" if not allow_zero else f"{field_name} cannot be negative"
            result.add_error(message, field_name.lower(), "not_positive")
    
    except (ValueError, TypeError):
        result.add_error(f"{field_name} must be a valid number", field_name.lower(), "invalid_number")
    
    return result

def validate_email(email: str, field_name: str = "Email") -> ValidationResult:
    """Validate email format"""
    result = ValidationResult()
    
    if not email:
        return result
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email.strip()):
        result.add_error(f"{field_name} format is invalid", field_name.lower(), "invalid_email")
    
    return result

def validate_phone(phone: str, field_name: str = "Phone") -> ValidationResult:
    """Validate phone number format"""
    result = ValidationResult()
    
    if not phone:
        return result
    
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', phone)
    
    # Indonesian phone number validation (8-15 digits)
    if len(digits) < 8 or len(digits) > 15:
        result.add_error(f"{field_name} must be 8-15 digits", field_name.lower(), "invalid_phone")
    
    return result

# ========== BUSINESS-SPECIFIC VALIDATORS ==========

def validate_npwp(npwp: str, field_name: str = "NPWP") -> ValidationResult:
    """Validate Indonesian NPWP format"""
    result = ValidationResult()
    
    if not npwp:
        result.add_error(f"{field_name} is required", field_name.lower(), "required")
        return result
    
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', npwp)
    
    # NPWP must be exactly 15 digits
    if len(digits) != 15:
        result.add_error(f"{field_name} must be exactly 15 digits", field_name.lower(), "invalid_npwp")
        return result
    
    # Basic checksum validation (simplified)
    # Real NPWP has complex checksum rules, this is basic validation
    if digits.startswith('00') or digits.endswith('000'):
        result.add_warning(f"{field_name} format may be invalid", field_name.lower(), "npwp_warning")
    
    return result

def validate_passport(passport: str, field_name: str = "Passport") -> ValidationResult:
    """Validate passport number format"""
    result = ValidationResult()
    
    if not passport:
        result.add_error(f"{field_name} is required", field_name.lower(), "required")
        return result
    
    # Clean passport (alphanumeric only)
    cleaned = re.sub(r'[^A-Za-z0-9]', '', passport)
    
    # Passport should be 6-20 alphanumeric characters
    if len(cleaned) < 6:
        result.add_error(f"{field_name} must be at least 6 characters", field_name.lower(), "too_short")
    elif len(cleaned) > 20:
        result.add_error(f"{field_name} cannot exceed 20 characters", field_name.lower(), "too_long")
    
    # Must contain at least one letter and one number (typical passport format)
    if not re.search(r'[A-Za-z]', cleaned) or not re.search(r'[0-9]', cleaned):
        result.add_warning(f"{field_name} should contain both letters and numbers", field_name.lower(), "passport_format")
    
    return result

def validate_gender(gender: str, field_name: str = "Gender") -> ValidationResult:
    """Validate gender value"""
    result = ValidationResult()
    
    valid_genders = ['Laki-laki', 'Perempuan']
    
    if gender not in valid_genders:
        result.add_error(
            f"{field_name} must be one of: {', '.join(valid_genders)}", 
            field_name.lower(), "invalid_gender"
        )
    
    return result

def validate_relationship(relationship: str, field_name: str = "Relationship") -> ValidationResult:
    """Validate family relationship value"""
    result = ValidationResult()
    
    valid_relationships = ['spouse', 'parent', 'child']
    
    if relationship not in valid_relationships:
        result.add_error(
            f"{field_name} must be one of: {', '.join(valid_relationships)}", 
            field_name.lower(), "invalid_relationship"
        )
    
    return result

def validate_invoice_status(status: str, field_name: str = "Status") -> ValidationResult:
    """Validate invoice status value"""
    result = ValidationResult()
    
    valid_statuses = ['draft', 'finalized', 'paid', 'cancelled']
    
    if status not in valid_statuses:
        result.add_error(
            f"{field_name} must be one of: {', '.join(valid_statuses)}", 
            field_name.lower(), "invalid_status"
        )
    
    return result

def validate_vat_percentage(percentage: Any, field_name: str = "VAT Percentage") -> ValidationResult:
    """Validate VAT percentage value"""
    result = ValidationResult()
    
    try:
        decimal_value = safe_decimal(percentage)
        
        if decimal_value < Decimal('0'):
            result.add_error(f"{field_name} cannot be negative", field_name.lower(), "negative_vat")
        elif decimal_value > Decimal('100'):
            result.add_error(f"{field_name} cannot exceed 100%", field_name.lower(), "excessive_vat")
        elif decimal_value > Decimal('50'):
            result.add_warning(f"{field_name} seems unusually high", field_name.lower(), "high_vat")
    
    except (ValueError, TypeError):
        result.add_error(f"{field_name} must be a valid percentage", field_name.lower(), "invalid_percentage")
    
    return result

# ========== ENTITY VALIDATORS ==========

def validate_user_data(user_data: Dict[str, Any]) -> ValidationResult:
    """Validate user data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['username', 'password_hash', 'full_name', 'role']
    for field in required_fields:
        field_result = validate_required(user_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Username validation
    username = user_data.get('username', '')
    if username:
        username_result = validate_string_length(username, 3, 50, "Username")
        if not username_result.is_valid:
            result.errors.extend(username_result.errors)
        
        # Username should be alphanumeric with underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            result.add_error("Username can only contain letters, numbers, and underscores", "username", "invalid_username")
    
    # Full name validation
    full_name = user_data.get('full_name', '')
    if full_name:
        name_result = validate_string_length(full_name, 2, 100, "Full name")
        if not name_result.is_valid:
            result.errors.extend(name_result.errors)
    
    # Role validation
    role = user_data.get('role', '')
    if role not in ['admin', 'viewer']:
        result.add_error("Role must be 'admin' or 'viewer'", "role", "invalid_role")
    
    return result

def validate_company_data(company_data: Dict[str, Any]) -> ValidationResult:
    """Validate company data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['company_name', 'npwp', 'idtku', 'address']
    for field in required_fields:
        field_result = validate_required(company_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Company name validation
    company_name = company_data.get('company_name', '')
    if company_name:
        name_result = validate_string_length(company_name, 2, 200, "Company name")
        if not name_result.is_valid:
            result.errors.extend(name_result.errors)
    
    # NPWP validation
    npwp = company_data.get('npwp', '')
    if npwp:
        npwp_result = validate_npwp(npwp)
        if not npwp_result.is_valid:
            result.errors.extend(npwp_result.errors)
        if npwp_result.warnings:
            result.warnings.extend(npwp_result.warnings)
    
    # IDTKU validation
    idtku = company_data.get('idtku', '')
    if idtku:
        idtku_result = validate_string_length(idtku, 5, 20, "IDTKU")
        if not idtku_result.is_valid:
            result.errors.extend(idtku_result.errors)
    
    # Address validation
    address = company_data.get('address', '')
    if address:
        address_result = validate_string_length(address, 10, 500, "Address")
        if not address_result.is_valid:
            result.errors.extend(address_result.errors)
    
    return result

def validate_tka_worker_data(tka_data: Dict[str, Any]) -> ValidationResult:
    """Validate TKA worker data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['nama', 'passport', 'jenis_kelamin']
    for field in required_fields:
        field_result = validate_required(tka_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Name validation
    nama = tka_data.get('nama', '')
    if nama:
        name_result = validate_string_length(nama, 2, 100, "Name")
        if not name_result.is_valid:
            result.errors.extend(name_result.errors)
    
    # Passport validation
    passport = tka_data.get('passport', '')
    if passport:
        passport_result = validate_passport(passport)
        if not passport_result.is_valid:
            result.errors.extend(passport_result.errors)
        if passport_result.warnings:
            result.warnings.extend(passport_result.warnings)
    
    # Gender validation
    jenis_kelamin = tka_data.get('jenis_kelamin', '')
    if jenis_kelamin:
        gender_result = validate_gender(jenis_kelamin)
        if not gender_result.is_valid:
            result.errors.extend(gender_result.errors)
    
    # Division validation (optional)
    divisi = tka_data.get('divisi', '')
    if divisi:
        divisi_result = validate_string_length(divisi, 1, 100, "Division")
        if not divisi_result.is_valid:
            result.errors.extend(divisi_result.errors)
    
    return result

def validate_job_description_data(job_data: Dict[str, Any]) -> ValidationResult:
    """Validate job description data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['company_id', 'job_name', 'job_description', 'price']
    for field in required_fields:
        field_result = validate_required(job_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Job name validation
    job_name = job_data.get('job_name', '')
    if job_name:
        name_result = validate_string_length(job_name, 2, 200, "Job name")
        if not name_result.is_valid:
            result.errors.extend(name_result.errors)
    
    # Job description validation
    job_description = job_data.get('job_description', '')
    if job_description:
        desc_result = validate_string_length(job_description, 5, 1000, "Job description")
        if not desc_result.is_valid:
            result.errors.extend(desc_result.errors)
    
    # Price validation
    price = job_data.get('price')
    if price is not None:
        price_result = validate_positive_number(price, "Price", allow_zero=False)
        if not price_result.is_valid:
            result.errors.extend(price_result.errors)
        
        # Check for reasonable price range
        price_range_result = validate_numeric_range(
            price, Decimal('1'), Decimal('999999999.99'), "Price"
        )
        if not price_range_result.is_valid:
            result.errors.extend(price_range_result.errors)
    
    return result

def validate_invoice_data(invoice_data: Dict[str, Any]) -> ValidationResult:
    """Validate invoice data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['company_id', 'invoice_date', 'created_by']
    for field in required_fields:
        field_result = validate_required(invoice_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Invoice number validation (if provided)
    invoice_number = invoice_data.get('invoice_number', '')
    if invoice_number:
        number_result = validate_string_length(invoice_number, 5, 50, "Invoice number")
        if not number_result.is_valid:
            result.errors.extend(number_result.errors)
    
    # Date validation
    invoice_date = invoice_data.get('invoice_date')
    if invoice_date:
        if isinstance(invoice_date, str):
            try:
                datetime.strptime(invoice_date, '%Y-%m-%d')
            except ValueError:
                result.add_error("Invoice date must be in YYYY-MM-DD format", "invoice_date", "invalid_date")
        elif isinstance(invoice_date, date):
            # Check if date is not too far in the future
            if invoice_date > date.today() + timedelta(days=30):
                result.add_warning("Invoice date is more than 30 days in the future", "invoice_date", "future_date")
    
    # VAT percentage validation
    vat_percentage = invoice_data.get('vat_percentage')
    if vat_percentage is not None:
        vat_result = validate_vat_percentage(vat_percentage)
        if not vat_result.is_valid:
            result.errors.extend(vat_result.errors)
        if vat_result.warnings:
            result.warnings.extend(vat_result.warnings)
    
    # Status validation
    status = invoice_data.get('status', 'draft')
    status_result = validate_invoice_status(status)
    if not status_result.is_valid:
        result.errors.extend(status_result.errors)
    
    return result

def validate_invoice_line_data(line_data: Dict[str, Any]) -> ValidationResult:
    """Validate invoice line data"""
    result = ValidationResult()
    
    # Required fields
    required_fields = ['invoice_id', 'tka_id', 'job_description_id', 'unit_price', 'quantity']
    for field in required_fields:
        field_result = validate_required(line_data.get(field), field.replace('_', ' ').title())
        if not field_result.is_valid:
            result.errors.extend(field_result.errors)
    
    # Quantity validation
    quantity = line_data.get('quantity')
    if quantity is not None:
        quantity_result = validate_numeric_range(
            quantity, Decimal('1'), Decimal('9999'), "Quantity"
        )
        if not quantity_result.is_valid:
            result.errors.extend(quantity_result.errors)
    
    # Unit price validation
    unit_price = line_data.get('unit_price')
    if unit_price is not None:
        price_result = validate_positive_number(unit_price, "Unit price", allow_zero=False)
        if not price_result.is_valid:
            result.errors.extend(price_result.errors)
        
        # Check reasonable price range
        price_range_result = validate_numeric_range(
            unit_price, Decimal('0.01'), Decimal('999999999.99'), "Unit price"
        )
        if not price_range_result.is_valid:
            result.errors.extend(price_range_result.errors)
    
    # Baris number validation
    baris = line_data.get('baris')
    if baris is not None:
        baris_result = validate_numeric_range(baris, Decimal('1'), Decimal('999'), "Line number")
        if not baris_result.is_valid:
            result.errors.extend(baris_result.errors)
    
    return result

# ========== BULK VALIDATION ==========

def validate_import_data(data_list: List[Dict[str, Any]], entity_type: str) -> Dict[int, ValidationResult]:
    """Validate list of data for import operations"""
    results = {}
    
    validator_map = {
        'company': validate_company_data,
        'tka_worker': validate_tka_worker_data,
        'job_description': validate_job_description_data,
        'invoice': validate_invoice_data,
        'invoice_line': validate_invoice_line_data
    }
    
    validator = validator_map.get(entity_type)
    if not validator:
        raise ValueError(f"Unknown entity type: {entity_type}")
    
    for index, data in enumerate(data_list):
        results[index] = validator(data)
    
    return results

if __name__ == "__main__":
    # Test validation functions
    print("Testing validation functions...")
    
    # Test company validation
    company_data = {
        'company_name': 'Test Company',
        'npwp': '12.345.678.9-012.345',
        'idtku': 'IDTKU123',
        'address': 'Test Address, Jakarta'
    }
    result = validate_company_data(company_data)
    print(f"Company validation: {'✅ Valid' if result.is_valid else '❌ Invalid'}")
    if result.errors:
        print(f"Errors: {[e['message'] for e in result.errors]}")
    
    # Test TKA validation
    tka_data = {
        'nama': 'John Doe',
        'passport': 'A1234567',
        'jenis_kelamin': 'Laki-laki',
        'divisi': 'Engineering'
    }
    result = validate_tka_worker_data(tka_data)
    print(f"TKA validation: {'✅ Valid' if result.is_valid else '❌ Invalid'}")
    
    print("✅ Validation functions test completed")