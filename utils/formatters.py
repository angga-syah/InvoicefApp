"""
Invoice Management System - Data Formatting Functions
Formatting functions for numbers, currency, dates, and text display.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Union, Optional, List
import locale
import logging

from utils.helpers import safe_decimal, number_to_words_indonesian

logger = logging.getLogger(__name__)

# ========== CURRENCY FORMATTERS ==========

def format_currency_idr(amount: Union[Decimal, float, str, int], 
                       show_symbol: bool = True, 
                       show_decimal: bool = False) -> str:
    """Format currency in Indonesian Rupiah format"""
    try:
        decimal_amount = safe_decimal(amount)
        
        # Convert to integer if not showing decimals
        if not show_decimal:
            decimal_amount = decimal_amount.quantize(Decimal('1'))
            formatted_number = f"{int(decimal_amount):,}"
        else:
            formatted_number = f"{decimal_amount:,.2f}"
        
        # Replace comma with dot for thousands separator (Indonesian format)
        formatted_number = formatted_number.replace(',', '.')
        
        if show_symbol:
            return f"Rp {formatted_number}"
        else:
            return formatted_number
            
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return "Rp 0"

def format_currency_input(amount: str) -> str:
    """Format currency input as user types"""
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', amount)
    
    if not digits:
        return ""
    
    # Convert to integer and format with thousands separator
    try:
        number = int(digits)
        formatted = f"{number:,}".replace(',', '.')
        return formatted
    except ValueError:
        return amount

def parse_currency_input(formatted_amount: str) -> Decimal:
    """Parse formatted currency input back to decimal"""
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', formatted_amount)
    
    if not digits:
        return Decimal('0')
    
    try:
        return Decimal(digits)
    except (ValueError, TypeError):
        return Decimal('0')

def format_currency_words(amount: Union[Decimal, float, str, int]) -> str:
    """Convert currency amount to words in Indonesian"""
    try:
        decimal_amount = safe_decimal(amount)
        integer_amount = int(decimal_amount)
        
        if integer_amount == 0:
            return "Nol Rupiah"
        
        words = number_to_words_indonesian(integer_amount)
        return f"{words} Rupiah"
        
    except Exception as e:
        logger.error(f"Error converting currency to words: {e}")
        return "Nol Rupiah"

# ========== NUMBER FORMATTERS ==========

def format_number(number: Union[int, float, Decimal, str], 
                 decimal_places: int = 0,
                 thousands_separator: str = ".") -> str:
    """Format number with thousands separator"""
    try:
        if isinstance(number, str):
            # Try to parse string number
            cleaned = re.sub(r'[^\d.-]', '', number)
            if not cleaned:
                return "0"
            number = float(cleaned)
        
        if decimal_places == 0:
            formatted = f"{int(number):,}"
        else:
            formatted = f"{float(number):,.{decimal_places}f}"
        
        # Replace comma with custom separator
        if thousands_separator != ",":
            formatted = formatted.replace(',', thousands_separator)
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting number: {e}")
        return "0"

def format_percentage(value: Union[float, Decimal, str], 
                     decimal_places: int = 2,
                     include_symbol: bool = True) -> str:
    """Format percentage value"""
    try:
        decimal_value = safe_decimal(value)
        formatted = f"{float(decimal_value):.{decimal_places}f}"
        
        if include_symbol:
            return f"{formatted}%"
        else:
            return formatted
            
    except Exception as e:
        logger.error(f"Error formatting percentage: {e}")
        return "0%"

def format_decimal_precision(value: Union[Decimal, float, str], 
                           precision: int = 2) -> str:
    """Format decimal with specific precision"""
    try:
        decimal_value = safe_decimal(value)
        return f"{float(decimal_value):.{precision}f}"
        
    except Exception as e:
        logger.error(f"Error formatting decimal: {e}")
        return "0.00"

# ========== DATE FORMATTERS ==========

def format_date_short(date_value: Union[date, datetime, str]) -> str:
    """Format date in short format (DD/MM/YYYY)"""
    try:
        if isinstance(date_value, str):
            # Try to parse string date
            if '-' in date_value:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
            else:
                return date_value
        elif isinstance(date_value, datetime):
            date_obj = date_value.date()
        elif isinstance(date_value, date):
            date_obj = date_value
        else:
            return ""
        
        return date_obj.strftime('%d/%m/%Y')
        
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return ""

def format_date_long(date_value: Union[date, datetime, str]) -> str:
    """Format date in long format (DD Month YYYY)"""
    try:
        if isinstance(date_value, str):
            if '-' in date_value:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
            else:
                return date_value
        elif isinstance(date_value, datetime):
            date_obj = date_value.date()
        elif isinstance(date_value, date):
            date_obj = date_value
        else:
            return ""
        
        # Indonesian month names
        months = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"
        
    except Exception as e:
        logger.error(f"Error formatting long date: {e}")
        return ""

def format_datetime(datetime_value: Union[datetime, str]) -> str:
    """Format datetime in readable format"""
    try:
        if isinstance(datetime_value, str):
            # Try to parse ISO datetime
            datetime_obj = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
        elif isinstance(datetime_value, datetime):
            datetime_obj = datetime_value
        else:
            return ""
        
        return datetime_obj.strftime('%d/%m/%Y %H:%M')
        
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return ""

def format_time_ago(datetime_value: Union[datetime, str]) -> str:
    """Format datetime as time ago (e.g., '2 hours ago')"""
    try:
        if isinstance(datetime_value, str):
            datetime_obj = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
        elif isinstance(datetime_value, datetime):
            datetime_obj = datetime_value
        else:
            return ""
        
        now = datetime.now()
        diff = now - datetime_obj
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "Baru saja"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} menit lalu"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} jam lalu"
        elif seconds < 2592000:  # 30 days
            days = int(seconds / 86400)
            return f"{days} hari lalu"
        else:
            return format_date_short(datetime_obj)
            
    except Exception as e:
        logger.error(f"Error formatting time ago: {e}")
        return ""

# ========== TEXT FORMATTERS ==========

def format_name_proper(name: str) -> str:
    """Format name with proper capitalization"""
    if not name:
        return ""
    
    # Split by space and capitalize each word
    words = name.strip().split()
    formatted_words = []
    
    for word in words:
        # Handle special cases for Indonesian names
        if word.lower() in ['bin', 'binti', 'van', 'de', 'del', 'da']:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.capitalize())
    
    return ' '.join(formatted_words)

def format_address_multiline(address: str, max_line_length: int = 40) -> str:
    """Format address with line breaks for better display"""
    if not address:
        return ""
    
    # Split by comma first
    parts = [part.strip() for part in address.split(',')]
    
    lines = []
    current_line = ""
    
    for part in parts:
        if len(current_line + part) <= max_line_length:
            if current_line:
                current_line += ", " + part
            else:
                current_line = part
        else:
            if current_line:
                lines.append(current_line)
            current_line = part
    
    if current_line:
        lines.append(current_line)
    
    return '\n'.join(lines)

def format_description_html(description: str) -> str:
    """Format description text for HTML display"""
    if not description:
        return ""
    
    # Replace line breaks with <br> tags
    formatted = description.replace('\n', '<br>')
    
    # Handle bullet points
    formatted = re.sub(r'^[-*•]\s*', '• ', formatted, flags=re.MULTILINE)
    
    return formatted

def format_phone_number(phone: str) -> str:
    """Format phone number for display"""
    if not phone:
        return ""
    
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', phone)
    
    if not digits:
        return phone
    
    # Format Indonesian phone numbers
    if digits.startswith('62'):
        # International format: +62 xxx xxx xxxx
        if len(digits) >= 10:
            return f"+62 {digits[2:5]} {digits[5:8]} {digits[8:]}"
    elif digits.startswith('0'):
        # Local format: 0xxx xxx xxxx
        if len(digits) >= 10:
            return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    
    # Default formatting for other formats
    if len(digits) >= 8:
        mid = len(digits) // 2
        return f"{digits[:mid]} {digits[mid:]}"
    
    return digits

def format_npwp_display(npwp: str) -> str:
    """Format NPWP for display"""
    if not npwp:
        return ""
    
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', npwp)
    
    # Format as XX.XXX.XXX.X-XXX.XXX
    if len(digits) == 15:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:15]}"
    
    return npwp

def format_passport_display(passport: str) -> str:
    """Format passport for display"""
    if not passport:
        return ""
    
    # Clean passport (remove spaces and special chars except hyphens)
    cleaned = re.sub(r'[^A-Za-z0-9-]', '', passport)
    
    # Convert to uppercase for consistency
    return cleaned.upper()

# ========== ID FORMATTERS ==========

def format_invoice_number(year: int, month: int, sequence: int, 
                         prefix: str = "INV", separator: str = "-") -> str:
    """Format invoice number according to template"""
    try:
        year_short = str(year)[-2:]  # Last 2 digits of year
        month_padded = f"{month:02d}"  # Zero-padded month
        sequence_padded = f"{sequence:03d}"  # Zero-padded sequence
        
        return f"{prefix}{separator}{year_short}{separator}{month_padded}{separator}{sequence_padded}"
        
    except Exception as e:
        logger.error(f"Error formatting invoice number: {e}")
        return f"{prefix}-00-00-000"

def generate_batch_id() -> str:
    """Generate batch ID for import operations"""
    import uuid
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    short_uuid = str(uuid.uuid4())[:8]
    return f"BATCH_{timestamp}_{short_uuid}"

# ========== STATUS FORMATTERS ==========

def format_status_display(status: str) -> str:
    """Format status for user-friendly display"""
    status_map = {
        'draft': 'Draft',
        'finalized': 'Finalized', 
        'paid': 'Paid',
        'cancelled': 'Cancelled',
        'active': 'Active',
        'inactive': 'Inactive'
    }
    
    return status_map.get(status.lower(), status.title())

def format_status_badge_class(status: str) -> str:
    """Get CSS class for status badge"""
    status_classes = {
        'draft': 'badge-warning',
        'finalized': 'badge-success',
        'paid': 'badge-info',
        'cancelled': 'badge-danger',
        'active': 'badge-success',
        'inactive': 'badge-secondary'
    }
    
    return status_classes.get(status.lower(), 'badge-light')

# ========== TABLE FORMATTERS ==========

def format_table_cell(value, cell_type: str = 'text', max_length: int = 50) -> str:
    """Format value for table cell display"""
    if value is None:
        return ""
    
    if cell_type == 'currency':
        return format_currency_idr(value, show_symbol=False)
    elif cell_type == 'date':
        return format_date_short(value)
    elif cell_type == 'datetime':
        return format_datetime(value)
    elif cell_type == 'percentage':
        return format_percentage(value)
    elif cell_type == 'number':
        return format_number(value)
    elif cell_type == 'status':
        return format_status_display(str(value))
    else:
        # Text formatting with truncation
        text = str(value)
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text

# ========== EXPORT FORMATTERS ==========

def format_excel_currency(amount: Union[Decimal, float, str]) -> float:
    """Format currency for Excel export (as number)"""
    try:
        return float(safe_decimal(amount))
    except Exception:
        return 0.0

def format_excel_date(date_value: Union[date, datetime, str]) -> str:
    """Format date for Excel export"""
    try:
        if isinstance(date_value, str):
            return date_value
        elif isinstance(date_value, datetime):
            return date_value.strftime('%Y-%m-%d')
        elif isinstance(date_value, date):
            return date_value.strftime('%Y-%m-%d')
        else:
            return ""
    except Exception:
        return ""

def format_csv_safe(text: str) -> str:
    """Format text for safe CSV export"""
    if not text:
        return ""
    
    # Replace newlines with spaces
    safe_text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Escape quotes
    safe_text = safe_text.replace('"', '""')
    
    # Remove any other problematic characters
    safe_text = re.sub(r'[^\w\s.,;:()\-\'"@/]', '', safe_text)
    
    return safe_text.strip()

# ========== UTILITY FORMATTERS ==========

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds} detik"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} menit"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} jam {minutes} menit"
        else:
            return f"{hours} jam"

def format_search_highlight(text: str, search_term: str) -> str:
    """Highlight search term in text"""
    if not search_term or not text:
        return text
    
    # Case-insensitive highlight
    pattern = re.escape(search_term)
    highlighted = re.sub(
        f'({pattern})', 
        r'<mark>\1</mark>', 
        text, 
        flags=re.IGNORECASE
    )
    
    return highlighted

# ========== VALIDATION FORMATTERS ==========

def format_validation_errors(errors: List) -> str:
    """Format validation errors for display"""
    if not errors:
        return ""
    
    if len(errors) == 1:
        error_item = errors[0]
        if isinstance(error_item, dict):
            return error_item.get('message', str(error_item))
        else:
            return str(error_item)
    
    # Multiple errors
    formatted_errors = []
    for i, error in enumerate(errors, 1):
        if isinstance(error, dict):
            message = error.get('message', str(error))
        else:
            message = str(error)
        formatted_errors.append(f"{i}. {message}")
    
    return '\n'.join(formatted_errors)

if __name__ == "__main__":
    # Test formatting functions
    print("Testing formatting functions...")
    
    # Test currency formatting
    print(f"Currency: {format_currency_idr(1234567.89)}")
    print(f"Currency words: {format_currency_words(1234567)}")
    
    # Test date formatting
    today = date.today()
    print(f"Date short: {format_date_short(today)}")
    print(f"Date long: {format_date_long(today)}")
    
    # Test number formatting
    print(f"Number: {format_number(1234567.89, 2)}")
    print(f"Percentage: {format_percentage(11.5)}")
    
    # Test text formatting
    print(f"Name: {format_name_proper('john doe bin ahmad')}")
    print(f"NPWP: {format_npwp_display('123456789012345')}")
    
    # Test invoice number
    print(f"Invoice: {format_invoice_number(2024, 12, 1)}")
    
    print("✅ Formatting functions test completed")