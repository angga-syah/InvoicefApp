"""
Invoice Management System - Common Utility Functions
Helper functions used throughout the application for common operations.
"""

import os
import re
import uuid
import json
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ========== STRING UTILITIES ==========

def clean_string(text: str) -> str:
    """Clean and normalize string input"""
    if not text:
        return ""
    return ' '.join(text.strip().split())

def normalize_name(name: str) -> str:
    """Normalize name with proper capitalization"""
    if not name:
        return ""
    # Clean and split by space
    words = clean_string(name).split()
    # Capitalize each word except common prefixes/suffixes
    normalized_words = []
    for word in words:
        # Handle special cases
        if word.lower() in ['van', 'de', 'del', 'da', 'bin', 'binti']:
            normalized_words.append(word.lower())
        else:
            normalized_words.append(word.capitalize())
    return ' '.join(normalized_words)

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string with suffix if too long"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def generate_slug(text: str) -> str:
    """Generate URL-friendly slug from text"""
    if not text:
        return ""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug.strip('-')

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data like account numbers"""
    if not data or len(data) <= visible_chars:
        return data
    
    if len(data) <= visible_chars * 2:
        # Show first and last few characters
        half = visible_chars // 2
        return data[:half] + mask_char * (len(data) - visible_chars) + data[-half:]
    else:
        # Show first and last visible_chars
        return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]

# ========== NUMBER UTILITIES ==========

def safe_decimal(value: Any, default: Decimal = Decimal('0')) -> Decimal:
    """Safely convert value to Decimal"""
    if value is None:
        return default
    
    try:
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, str):
            # Clean string first
            cleaned = re.sub(r'[^\d.-]', '', value)
            return Decimal(cleaned) if cleaned else default
        else:
            return default
    except (ValueError, TypeError):
        return default

def round_currency(amount: Union[Decimal, float, str], precision: int = 0) -> Decimal:
    """Round currency amount to specified precision"""
    decimal_amount = safe_decimal(amount)
    if precision == 0:
        return decimal_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        quantizer = Decimal('0.1') ** precision
        return decimal_amount.quantize(quantizer, rounding=ROUND_HALF_UP)

def calculate_percentage(part: Union[Decimal, float], total: Union[Decimal, float]) -> Decimal:
    """Calculate percentage safely"""
    part_decimal = safe_decimal(part)
    total_decimal = safe_decimal(total)
    
    if total_decimal == 0:
        return Decimal('0')
    
    return (part_decimal / total_decimal) * 100

def parse_number_string(text: str) -> Optional[Decimal]:
    """Parse number from string with various formats"""
    if not text:
        return None
    
    # Remove common thousand separators and currency symbols
    cleaned = re.sub(r'[Rp\s,.]', '', text)
    cleaned = re.sub(r'[^\d-]', '', cleaned)
    
    try:
        return Decimal(cleaned)
    except (ValueError, TypeError):
        return None

# ========== DATE UTILITIES ==========

def safe_date_parse(date_value: Any) -> Optional[date]:
    """Safely parse date from various formats"""
    if date_value is None:
        return None
    
    if isinstance(date_value, date):
        return date_value
    
    if isinstance(date_value, datetime):
        return date_value.date()
    
    if isinstance(date_value, str):
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d %B %Y',
            '%d %b %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt).date()
            except ValueError:
                continue
    
    return None

def format_date_indonesian(date_value: date) -> str:
    """Format date in Indonesian format"""
    if not date_value:
        return ""
    
    months = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    
    return f"{date_value.day} {months[date_value.month - 1]} {date_value.year}"

def get_date_range(period: str) -> tuple:
    """Get date range for common periods"""
    today = date.today()
    
    if period == 'today':
        return today, today
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == 'this_month':
        start = today.replace(day=1)
        return start, today
    elif period == 'last_month':
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return first_day_last_month, last_day_last_month
    elif period == 'this_year':
        start = today.replace(month=1, day=1)
        return start, today
    else:
        return today, today

def calculate_age(birth_date: date, reference_date: Optional[date] = None) -> int:
    """Calculate age from birth date"""
    if not birth_date:
        return 0
    
    if reference_date is None:
        reference_date = date.today()
    
    age = reference_date.year - birth_date.year
    if reference_date < birth_date.replace(year=reference_date.year):
        age -= 1
    
    return max(0, age)

# ========== FILE UTILITIES ==========

def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not"""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def get_file_size_string(size_bytes: int) -> str:
    """Convert file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def safe_filename(filename: str) -> str:
    """Create safe filename by removing invalid characters"""
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing dots and spaces
    safe = safe.strip('. ')
    # Limit length
    if len(safe) > 200:
        name, ext = os.path.splitext(safe)
        safe = name[:200-len(ext)] + ext
    
    return safe or 'unnamed'

def get_unique_filename(directory: Path, filename: str) -> str:
    """Get unique filename in directory by adding number suffix if needed"""
    base_path = directory / filename
    if not base_path.exists():
        return filename
    
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{name}_{counter}{ext}"
        if not (directory / new_filename).exists():
            return new_filename
        counter += 1

# ========== COLLECTION UTILITIES ==========

def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with nested key support"""
    if not isinstance(dictionary, dict):
        return default
    
    # Support nested keys with dot notation
    keys = key.split('.')
    value = dictionary
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def remove_duplicates(lst: List, key_func=None) -> List:
    """Remove duplicates from list, optionally using key function"""
    if key_func is None:
        return list(dict.fromkeys(lst))
    else:
        seen = set()
        result = []
        for item in lst:
            key = key_func(item)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

# ========== ID AND UUID UTILITIES ==========

def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())

def is_valid_uuid(uuid_string: str) -> bool:
    """Check if string is valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def generate_short_id(length: int = 8) -> str:
    """Generate short random ID"""
    import string
    import random
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

# ========== JSON UTILITIES ==========

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON string"""
    try:
        return json.loads(json_string) if json_string else default
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely serialize object to JSON"""
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return default

# ========== SEARCH UTILITIES ==========

def fuzzy_search_score(query: str, text: str) -> float:
    """Calculate fuzzy search score between query and text"""
    if not query or not text:
        return 0.0
    
    query = query.lower().strip()
    text = text.lower().strip()
    
    # Exact match
    if query == text:
        return 1.0
    
    # Starts with
    if text.startswith(query):
        return 0.9
    
    # Contains
    if query in text:
        return 0.7
    
    # Word matching
    query_words = set(query.split())
    text_words = set(text.split())
    common_words = query_words.intersection(text_words)
    
    if common_words:
        return len(common_words) / len(query_words) * 0.6
    
    # Character similarity
    from difflib import SequenceMatcher
    return SequenceMatcher(None, query, text).ratio() * 0.5

def highlight_search_term(text: str, query: str, highlight_tag: str = "<mark>") -> str:
    """Highlight search term in text"""
    if not query or not text:
        return text
    
    close_tag = highlight_tag.replace('<', '</')
    pattern = re.escape(query)
    return re.sub(pattern, f"{highlight_tag}{query}{close_tag}", text, flags=re.IGNORECASE)

# ========== BUSINESS UTILITIES ==========

def format_npwp(npwp: str) -> str:
    """Format NPWP with standard formatting"""
    if not npwp:
        return ""
    
    # Remove all non-digits
    digits = re.sub(r'[^\d]', '', npwp)
    
    # Format as XX.XXX.XXX.X-XXX.XXX
    if len(digits) == 15:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:15]}"
    
    return npwp

def validate_passport(passport: str) -> bool:
    """Validate passport number format"""
    if not passport:
        return False
    
    # Basic validation - alphanumeric, 6-20 characters
    cleaned = re.sub(r'[^A-Za-z0-9]', '', passport)
    return 6 <= len(cleaned) <= 20

# ========== ERROR HANDLING UTILITIES ==========

def safe_execute(func, *args, default=None, **kwargs):
    """Safely execute function with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return default

def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """Retry function on failure with exponential backoff"""
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)

# ========== LOGGING UTILITIES ==========

def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None):
    """Log function call with parameters"""
    args_str = str(args) if args else ""
    kwargs_str = str(kwargs) if kwargs else ""
    logger.debug(f"Calling {func_name}({args_str}, {kwargs_str})")

def log_performance(func):
    """Decorator to log function performance"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper

# ========== CONVERSION UTILITIES ==========

def number_to_words_indonesian(number: Union[int, float, Decimal]) -> str:
    """Convert number to Indonesian words"""
    try:
        import num2words
        # Convert to integer for num2words
        num = int(safe_decimal(number))
        words = num2words.num2words(num, lang='id')
        return words.capitalize()
    except ImportError:
        # Fallback simple implementation
        return f"Angka {number}"
    except Exception:
        return "Nol"

if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")
    
    # Test string utilities
    print(f"Normalize name: {normalize_name('john doe van')}")
    print(f"Clean string: {clean_string('  hello   world  ')}")
    print(f"Mask data: {mask_sensitive_data('1234567890123456')}")
    
    # Test number utilities
    print(f"Safe decimal: {safe_decimal('Rp 1,234.56')}")
    print(f"Round currency: {round_currency(1234.567)}")
    
    # Test date utilities
    print(f"Indonesian date: {format_date_indonesian(date.today())}")
    
    # Test fuzzy search
    print(f"Fuzzy score: {fuzzy_search_score('john', 'John Doe')}")
    
    print("✅ Utility functions test completed")