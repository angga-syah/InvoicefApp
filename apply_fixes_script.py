#!/usr/bin/env python3
"""
Apply Type Error Fixes Script
Automatically applies common type error fixes to Python files.
"""

import re
import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def backup_file(file_path: Path) -> Path:
    """Create a backup of the original file"""
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")
    return backup_path

def apply_common_fixes(content: str) -> Tuple[str, List[str]]:
    """Apply common type error fixes to file content"""
    fixes_applied = []
    
    # Fix 1: Add typing imports
    if "from typing import" not in content and any(hint in content for hint in ["Optional", "List", "Dict", "Union"]):
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        typing_import = "from typing import Optional, List, Dict, Any, Union"
        lines.insert(import_index, typing_import)
        content = '\n'.join(lines)
        fixes_applied.append("Added typing imports")
    
    # Fix 2: Replace None default parameters with Optional
    def fix_optional_params(match):
        param_name = match.group(1)
        param_type = match.group(2)
        if param_type and "Optional" not in param_type:
            return f"{param_name}: Optional[{param_type}] = None"
        return match.group(0)
    
    optional_pattern = r'(\w+):\s*([^=\s]+)\s*=\s*None'
    new_content = re.sub(optional_pattern, fix_optional_params, content)
    if new_content != content:
        content = new_content
        fixes_applied.append("Fixed Optional parameter types")
    
    # Fix 3: Add safe_decimal calls for Decimal operations
    decimal_patterns = [
        (r'Decimal\((\w+)\)', r'safe_decimal(\1)'),
        (r'Decimal\(str\(([^)]+)\)\)', r'safe_decimal(\1)')
    ]
    
    for pattern, replacement in decimal_patterns:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            fixes_applied.append("Added safe_decimal calls")
    
    # Fix 4: Add null checks for SQLAlchemy operations
    nullable_patterns = [
        (r'if\s+(\w+)\.(\w+):', r'if \1.\2 is not None and \1.\2:'),
        (r'(\w+)\.(\w+)\s*==', r'\1.\2 is not None and \1.\2 ==')
    ]
    
    for pattern, replacement in nullable_patterns:
        # Only apply if it looks like a SQLAlchemy column access
        if re.search(r'\.filter\(|\.query\(', content):
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                fixes_applied.append("Added null safety checks")
    
    # Fix 5: Add proper exception handling
    try_pattern = r'(\s+)(return\s+\w+\([^)]+\))'
    def add_try_catch(match):
        indent = match.group(1)
        return_stmt = match.group(2)
        return f"""{indent}try:
{indent}    {return_stmt}
{indent}except (ValueError, TypeError):
{indent}    return None"""
    
    # Only apply to specific patterns that commonly fail
    if "Decimal(" in content or "int(" in content:
        new_content = re.sub(try_pattern, add_try_catch, content)
        if new_content != content and "try:" not in content:
            content = new_content
            fixes_applied.append("Added exception handling")
    
    # Fix 6: Import text from sqlalchemy for raw SQL
    if "session.execute(" in content and "text(" in content and "from sqlalchemy import" in content:
        content = re.sub(
            r'from sqlalchemy import ([^n]+)(?!.*text)',
            r'from sqlalchemy import \1, text',
            content
        )
        if "text" not in content:
            fixes_applied.append("Added text import for SQLAlchemy")
    
    # Fix 7: Fix string formatting issues
    content = re.sub(r"f'%\{([^}]+)\}%'", r"f'%{\\1}%'", content)
    
    return content, fixes_applied

def process_file(file_path: Path) -> bool:
    """Process a single Python file"""
    logger.info(f"Processing: {file_path}")
    
    try:
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes
        fixed_content, fixes_applied = apply_common_fixes(original_content)
        
        if fixes_applied:
            # Create backup
            backup_path = backup_file(file_path)
            
            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            logger.info(f"✅ Applied fixes to {file_path}:")
            for fix in fixes_applied:
                logger.info(f"   - {fix}")
            
            return True
        else:
            logger.info(f"No fixes needed for {file_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing {file_path}: {e}")
        return False

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory"""
    python_files = []
    
    for pattern in ["*.py"]:
        python_files.extend(directory.rglob(pattern))
    
    # Filter out __pycache__ and other unwanted directories
    filtered_files = []
    for file_path in python_files:
        if not any(part.startswith('.') or part == '__pycache__' for part in file_path.parts):
            filtered_files.append(file_path)
    
    return filtered_files

def main():
    """Main function"""
    logger.info("🔧 Starting automatic type error fixes...")
    
    # Get current directory
    current_dir = Path.cwd()
    logger.info(f"Working directory: {current_dir}")
    
    # Find Python files
    python_files = find_python_files(current_dir)
    logger.info(f"Found {len(python_files)} Python files")
    
    if not python_files:
        logger.warning("No Python files found")
        return
    
    # Process files
    processed_files = 0
    fixed_files = 0
    
    for file_path in python_files:
        # Skip certain files
        if any(skip in str(file_path) for skip in ['test_', 'setup.py', '__init__.py']):
            continue
            
        processed_files += 1
        if process_file(file_path):
            fixed_files += 1
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("FIX SUMMARY")
    logger.info("="*50)
    logger.info(f"Files processed: {processed_files}")
    logger.info(f"Files fixed: {fixed_files}")
    logger.info(f"Files unchanged: {processed_files - fixed_files}")
    
    if fixed_files > 0:
        logger.info("\n⚠️  IMPORTANT:")
        logger.info("- Backup files have been created with .backup extension")
        logger.info("- Please review the changes before committing")
        logger.info("- Run the validation script to verify fixes")
        logger.info("- Test your application thoroughly")
    
    logger.info("\n🎉 Automatic fixes completed!")

if __name__ == "__main__":
    main()