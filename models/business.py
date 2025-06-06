"""
Invoice Management System - Business Logic Layer
Core business logic and rules implementation for the application.
"""

import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
import logging
import io
import csv

from models.database import (
    User, Company, TkaWorker, TkaFamilyMember, JobDescription, 
    Invoice, InvoiceLine, BankAccount, Setting, InvoiceNumberSequence,
    safe_decimal_conversion, safe_float_conversion, safe_int_conversion,
    safe_string_conversion, safe_bool_check
)
from utils.helpers import safe_decimal, fuzzy_search_score
from utils.validators import ValidationResult
from utils.formatters import format_invoice_number

logger = logging.getLogger(__name__)

class BusinessError(Exception):
    """Custom exception for business logic errors"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        self.message = message
        self.code = code or "BUSINESS_ERROR"
        self.details = details or {}
        super().__init__(message)

class InvoiceBusinessLogic:
    """Core business logic for invoice operations"""
    
    def __init__(self, session: Session):
        self.session = session
        
    def calculate_vat_amount(self, subtotal: Decimal, vat_percentage: Decimal) -> Decimal:
        """
        Calculate VAT amount with special business rules:
        - .49 rounds down (18.000,49 → 18.000)
        - .50 rounds up (18.000,50 → 18.001)
        """
        # Ensure we have proper Decimal values
        subtotal_decimal = safe_decimal(subtotal)
        vat_percentage_decimal = safe_decimal(vat_percentage)
        
        vat_raw = subtotal_decimal * vat_percentage_decimal / 100
        decimal_part = vat_raw - vat_raw.quantize(Decimal('1'))
        
        if abs(decimal_part - Decimal('0.49')) < Decimal('0.001'):
            # Special rule for .49
            return vat_raw.quantize(Decimal('1'), rounding='ROUND_DOWN')
        elif decimal_part >= Decimal('0.50'):
            # .50 and above rounds up
            return vat_raw.quantize(Decimal('1'), rounding='ROUND_UP')
        else:
            # Standard rounding for other cases
            return vat_raw.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    def calculate_invoice_totals(self, invoice: Invoice) -> Dict[str, Decimal]:
        """Calculate all invoice totals"""
        # Calculate subtotal from invoice lines
        subtotal = Decimal('0')
        for line in invoice.lines:
            line_total = line.get_line_total_as_decimal()
            subtotal += line_total
        
        # Get VAT percentage safely
        vat_percentage = invoice.get_vat_percentage_as_decimal()
        
        # Calculate VAT amount
        vat_amount = self.calculate_vat_amount(subtotal, vat_percentage)
        total_amount = subtotal + vat_amount
        
        return {
            'subtotal': subtotal,
            'vat_amount': vat_amount,
            'total_amount': total_amount
        }
    
    def update_invoice_totals(self, invoice: Invoice) -> None:
        """Update invoice totals based on line items"""
        totals = self.calculate_invoice_totals(invoice)
        
        # Manual assignment to avoid SQLAlchemy type issues
        # These values will be converted by SQLAlchemy when saving
        invoice.subtotal = totals['subtotal']  # type: ignore
        invoice.vat_amount = totals['vat_amount']  # type: ignore
        invoice.total_amount = totals['total_amount']  # type: ignore
    
    def generate_invoice_number(self, invoice_date: Optional[date] = None) -> str:
        """Generate next invoice number with format INV-YY-MM-NNN"""
        if invoice_date is None:
            invoice_date = date.today()
        
        year = invoice_date.year
        month = invoice_date.month
        
        # Get or create sequence for this year/month
        sequence = self.session.query(InvoiceNumberSequence).filter(
            and_(
                InvoiceNumberSequence.year == year,
                InvoiceNumberSequence.month == month
            )
        ).first()
        
        if not sequence:
            sequence = InvoiceNumberSequence(
                year=year,
                month=month,
                current_number=0,
                prefix='INV'
            )
            self.session.add(sequence)
        
        # Increment sequence safely
        current_num = sequence.get_current_number_as_int()
        new_current_num = current_num + 1
        sequence.current_number = new_current_num  # type: ignore
        
        # Generate invoice number using the integer value
        invoice_number = format_invoice_number(year, month, new_current_num)
        
        # Check for collisions (safety measure)
        existing = self.session.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()
        
        if existing:
            # If collision exists, increment and try again
            new_current_num += 1
            sequence.current_number = new_current_num  # type: ignore
            invoice_number = format_invoice_number(year, month, new_current_num)
        
        return invoice_number
    
    def validate_invoice_transition(self, current_status: str, new_status: str) -> bool:
        """Validate if status transition is allowed"""
        allowed_transitions = {
            'draft': ['finalized', 'cancelled'],
            'finalized': ['paid', 'cancelled'],
            'paid': ['cancelled'],  # Only admin can cancel paid invoices
            'cancelled': []  # Cannot transition from cancelled
        }
        
        return new_status in allowed_transitions.get(current_status, [])
    
    def can_edit_invoice(self, invoice: Invoice) -> bool:
        """Check if invoice can be edited"""
        # Safe status check
        status = safe_string_conversion(invoice.status)
        return status in ['draft', 'finalized']
    
    def can_delete_invoice(self, invoice: Invoice) -> bool:
        """Check if invoice can be deleted"""
        # Safe status check
        status = safe_string_conversion(invoice.status)
        return status in ['draft', 'finalized']
    
    def validate_tka_assignment(self, tka_id: int, company_id: int) -> bool:
        """Validate if TKA can be assigned to company (through invoice history)"""
        # Check if TKA has been previously assigned to this company
        existing_assignment = self.session.query(InvoiceLine).join(Invoice).filter(
            and_(
                InvoiceLine.tka_id == tka_id,
                Invoice.company_id == company_id
            )
        ).first()
        
        # For now, allow any assignment (business rule can be tightened later)
        return True
    
    def get_default_bank_account(self) -> Optional[BankAccount]:
        """Get default bank account"""
        return self.session.query(BankAccount).filter(
            and_(
                BankAccount.is_default == True,
                BankAccount.is_active == True
            )
        ).first()

class SearchHelper:
    """Helper class for search operations with fuzzy matching"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def search_companies(self, query: str, limit: int = 50) -> List[Company]:
        """Search companies with fuzzy matching"""
        if not query:
            return self.session.query(Company).filter(
                Company.is_active == True
            ).order_by(Company.company_name).limit(limit).all()
        
        # Build filter conditions manually to avoid SQLAlchemy type issues
        query_pattern = f'{query}%'
        
        # Exact and prefix matches first
        exact_results = self.session.query(Company).filter(
            and_(
                Company.is_active == True,
                or_(
                    Company.company_name.ilike(query_pattern),
                    Company.npwp.like(query_pattern),
                    Company.idtku.ilike(query_pattern)
                )
            )
        ).order_by(Company.company_name).limit(limit // 2).all()
        
        # Fuzzy search for remaining slots
        if len(exact_results) < limit:
            remaining_limit = limit - len(exact_results)
            
            # Get companies not in exact results
            exact_ids = [c.id for c in exact_results]
            filter_condition = Company.is_active == True
            if exact_ids:
                filter_condition = and_(filter_condition, ~Company.id.in_(exact_ids))
                
            fuzzy_candidates = self.session.query(Company).filter(
                filter_condition
            ).all()
            
            # Score and sort fuzzy results
            scored_results = []
            for company in fuzzy_candidates:
                # Safe string conversion for fuzzy search
                company_name = safe_string_conversion(company.company_name)
                npwp = safe_string_conversion(company.npwp)
                idtku = safe_string_conversion(company.idtku)
                
                score = max(
                    fuzzy_search_score(query, company_name),
                    fuzzy_search_score(query, npwp),
                    fuzzy_search_score(query, idtku)
                )
                if score > 0.3:  # Minimum relevance threshold
                    scored_results.append((score, company))
            
            # Sort by score and take top results
            scored_results.sort(reverse=True, key=lambda x: x[0])
            fuzzy_results = [company for _, company in scored_results[:remaining_limit]]
            
            return exact_results + fuzzy_results
        
        return exact_results
    
    def search_tka_workers(self, query: str, limit: int = 50) -> List[Union[TkaWorker, TkaFamilyMember]]:
        """Search TKA workers and family members with fuzzy matching"""
        if not query:
            workers = self.session.query(TkaWorker).filter(
                TkaWorker.is_active == True
            ).order_by(TkaWorker.nama).limit(limit // 2).all()
            
            family = self.session.query(TkaFamilyMember).filter(
                TkaFamilyMember.is_active == True
            ).order_by(TkaFamilyMember.nama).limit(limit // 2).all()
            
            return workers + family
        
        # Search workers with pattern matching
        query_pattern = f'%{query}%'
        
        # Build conditions for worker search
        worker_conditions = [
            TkaWorker.is_active == True,
            or_(
                TkaWorker.nama.ilike(query_pattern),
                TkaWorker.passport.ilike(query_pattern)
            )
        ]
        
        # Add division condition only if the column has value
        # Using a subquery to check for non-null/non-empty division
        worker_conditions.append(
            or_(
                TkaWorker.nama.ilike(query_pattern),
                TkaWorker.passport.ilike(query_pattern),
                and_(
                    TkaWorker.divisi.isnot(None),
                    TkaWorker.divisi != '',
                    TkaWorker.divisi.ilike(query_pattern)
                )
            )
        )
        
        worker_results = self.session.query(TkaWorker).filter(
            and_(TkaWorker.is_active == True, worker_conditions[-1])
        ).order_by(TkaWorker.nama).limit(limit // 2).all()
        
        # Search family members
        family_results = self.session.query(TkaFamilyMember).filter(
            and_(
                TkaFamilyMember.is_active == True,
                or_(
                    TkaFamilyMember.nama.ilike(query_pattern),
                    TkaFamilyMember.passport.ilike(query_pattern)
                )
            )
        ).order_by(TkaFamilyMember.nama).limit(limit // 2).all()
        
        return worker_results + family_results
    
    def search_invoices(self, query: str, limit: int = 50) -> List[Invoice]:
        """Search invoices"""
        if not query:
            return self.session.query(Invoice).order_by(
                desc(Invoice.invoice_date), desc(Invoice.created_at)
            ).limit(limit).all()
        
        query_pattern = f'%{query}%'
        
        return self.session.query(Invoice).join(Company).filter(
            or_(
                Invoice.invoice_number.ilike(query_pattern),
                Company.company_name.ilike(query_pattern),
                Company.npwp.like(query_pattern)
            )
        ).order_by(
            desc(Invoice.invoice_date), desc(Invoice.created_at)
        ).limit(limit).all()

class DataHelper:
    """Helper class for common data operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_active_companies(self) -> List[Company]:
        """Get all active companies"""
        return self.session.query(Company).filter(
            Company.is_active == True
        ).order_by(Company.company_name).all()
    
    def get_company_job_descriptions(self, company_id: int) -> List[JobDescription]:
        """Get active job descriptions for a company"""
        return self.session.query(JobDescription).filter(
            and_(
                JobDescription.company_id == company_id,
                JobDescription.is_active == True
            )
        ).order_by(JobDescription.sort_order, JobDescription.job_name).all()
    
    def get_active_tka_workers(self) -> List[TkaWorker]:
        """Get all active TKA workers"""
        return self.session.query(TkaWorker).filter(
            TkaWorker.is_active == True
        ).order_by(TkaWorker.nama).all()
    
    def get_tka_family_members(self, tka_id: int) -> List[TkaFamilyMember]:
        """Get family members for a TKA worker"""
        return self.session.query(TkaFamilyMember).filter(
            and_(
                TkaFamilyMember.tka_id == tka_id,
                TkaFamilyMember.is_active == True
            )
        ).order_by(TkaFamilyMember.nama).all()
    
    def get_recent_invoices(self, limit: int = 10) -> List[Invoice]:
        """Get recent invoices"""
        return self.session.query(Invoice).order_by(
            desc(Invoice.created_at)
        ).limit(limit).all()
    
    def get_invoice_summary_stats(self) -> Dict[str, Any]:
        """Get invoice summary statistics"""
        # Total invoices by status
        status_counts = self.session.query(
            Invoice.status, func.count(Invoice.id)
        ).group_by(Invoice.status).all()
        
        # Total amounts by status
        status_amounts = self.session.query(
            Invoice.status, func.sum(Invoice.total_amount)
        ).group_by(Invoice.status).all()
        
        # Monthly totals (current year)
        current_year = date.today().year
        monthly_totals = self.session.query(
            func.extract('month', Invoice.invoice_date).label('month'),
            func.sum(Invoice.total_amount).label('total')
        ).filter(
            func.extract('year', Invoice.invoice_date) == current_year
        ).group_by(func.extract('month', Invoice.invoice_date)).all()
        
        # Convert query results to dictionaries safely
        status_counts_dict = {}
        for status, count in status_counts:
            status_str = safe_string_conversion(status)
            count_int = safe_int_conversion(count)
            status_counts_dict[status_str] = count_int
            
        status_amounts_dict = {}
        for status, amount in status_amounts:
            status_str = safe_string_conversion(status)
            amount_float = safe_float_conversion(amount)
            status_amounts_dict[status_str] = amount_float
            
        monthly_totals_dict = {}
        for month, total in monthly_totals:
            month_int = safe_int_conversion(month)
            total_float = safe_float_conversion(total)
            monthly_totals_dict[month_int] = total_float
        
        return {
            'status_counts': status_counts_dict,
            'status_amounts': status_amounts_dict,
            'monthly_totals': monthly_totals_dict
        }
    
    def check_duplicate_passport(self, passport: str, exclude_id: Optional[int] = None) -> bool:
        """Check if passport number already exists"""
        query = self.session.query(TkaWorker).filter(
            TkaWorker.passport == passport
        )
        
        if exclude_id:
            query = query.filter(TkaWorker.id != exclude_id)
        
        worker_exists = query.first() is not None
        
        # Also check family members
        family_query = self.session.query(TkaFamilyMember).filter(
            TkaFamilyMember.passport == passport
        )
        
        family_exists = family_query.first() is not None
        
        return worker_exists or family_exists
    
    def check_duplicate_npwp(self, npwp: str, exclude_id: Optional[int] = None) -> bool:
        """Check if NPWP already exists"""
        query = self.session.query(Company).filter(
            Company.npwp == npwp
        )
        
        if exclude_id:
            query = query.filter(Company.id != exclude_id)
        
        return query.first() is not None
    
    def check_duplicate_idtku(self, idtku: str, exclude_id: Optional[int] = None) -> bool:
        """Check if IDTKU already exists"""
        query = self.session.query(Company).filter(
            Company.idtku == idtku
        )
        
        if exclude_id:
            query = query.filter(Company.id != exclude_id)
        
        return query.first() is not None

class ValidationHelper:
    """Helper class for business rule validations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.data_helper = DataHelper(session)
    
    def validate_unique_passport(self, passport: str, exclude_id: Optional[int] = None) -> ValidationResult:
        """Validate passport uniqueness"""
        result = ValidationResult()
        
        if self.data_helper.check_duplicate_passport(passport, exclude_id):
            result.add_error(
                f"Passport number '{passport}' already exists",
                "passport",
                "duplicate_passport"
            )
        
        return result
    
    def validate_unique_npwp(self, npwp: str, exclude_id: Optional[int] = None) -> ValidationResult:
        """Validate NPWP uniqueness"""
        result = ValidationResult()
        
        if self.data_helper.check_duplicate_npwp(npwp, exclude_id):
            result.add_error(
                f"NPWP '{npwp}' already exists",
                "npwp",
                "duplicate_npwp"
            )
        
        return result
    
    def validate_unique_idtku(self, idtku: str, exclude_id: Optional[int] = None) -> ValidationResult:
        """Validate IDTKU uniqueness"""
        result = ValidationResult()
        
        if self.data_helper.check_duplicate_idtku(idtku, exclude_id):
            result.add_error(
                f"IDTKU '{idtku}' already exists",
                "idtku",
                "duplicate_idtku"
            )
        
        return result
    
    def validate_tka_company_assignment(self, tka_id: int, company_id: int) -> ValidationResult:
        """Validate TKA assignment to company"""
        result = ValidationResult()
        
        # Business rule: TKA can be assigned to any company
        # This can be enhanced with more specific rules if needed
        
        return result
    
    def validate_invoice_line_consistency(self, lines: List[Dict]) -> ValidationResult:
        """Validate invoice line consistency"""
        result = ValidationResult()
        
        if not lines:
            result.add_error("Invoice must have at least one line item", "lines", "no_lines")
            return result
        
        # Check for duplicate TKA-Job combinations
        seen_combinations = set()
        for line in lines:
            combination = (line.get('tka_id'), line.get('job_description_id'))
            if combination in seen_combinations:
                result.add_warning(
                    "Duplicate TKA-Job combination found",
                    "lines",
                    "duplicate_combination"
                )
            seen_combinations.add(combination)
        
        return result

class SettingsHelper:
    """Helper class for application settings"""
    
    def __init__(self, session: Session):
        self.session = session
        self._cache = {}
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value with caching"""
        if key in self._cache:
            return self._cache[key]
        
        setting = self.session.query(Setting).filter(
            Setting.setting_key == key
        ).first()
        
        if setting:
            value = setting.get_typed_value()
            self._cache[key] = value
            return value
        
        return default
    
    def set_setting(self, key: str, value: Any, user_id: Optional[int] = None) -> None:
        """Set setting value"""
        setting = self.session.query(Setting).filter(
            Setting.setting_key == key
        ).first()
        
        if setting:
            setting.setting_value = str(value)  # type: ignore
            setting.updated_by = user_id  # type: ignore
        else:
            setting = Setting(
                setting_key=key,
                setting_value=str(value),
                updated_by=user_id
            )
            self.session.add(setting)
        
        # Update cache
        self._cache[key] = value
    
    def get_default_vat_percentage(self) -> Decimal:
        """Get default VAT percentage"""
        vat_setting = self.get_setting('default_vat_percentage', '11.00')
        return safe_decimal(vat_setting)
    
    def get_invoice_number_format(self) -> str:
        """Get invoice number format"""
        format_setting = self.get_setting('invoice_number_format', 'INV-{YY}-{MM}-{NNN}')
        return safe_string_conversion(format_setting)
    
    def get_company_tagline(self) -> str:
        """Get company tagline"""
        tagline_setting = self.get_setting('company_tagline', 'Spirit of Services')
        return safe_string_conversion(tagline_setting)

class ReportHelper:
    """Helper class for report generation"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_invoice_report_data(self, start_date: Optional[date] = None, end_date: Optional[date] = None,
                              company_ids: Optional[List[int]] = None, status: Optional[str] = None) -> List[Dict]:
        """Get invoice data for reports"""
        query = self.session.query(Invoice).join(Company)
        
        # Apply filters
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)
        
        if company_ids:
            query = query.filter(Invoice.company_id.in_(company_ids))
        
        if status:
            query = query.filter(Invoice.status == status)
        
        invoices = query.order_by(desc(Invoice.invoice_date)).all()
        
        return [invoice.to_dict() for invoice in invoices]
    
    def get_company_summary(self, company_id: int, year: Optional[int] = None) -> Dict:
        """Get summary for a specific company"""
        query = self.session.query(Invoice).filter(
            Invoice.company_id == company_id
        )
        
        if year:
            query = query.filter(
                func.extract('year', Invoice.invoice_date) == year
            )
        
        invoices = query.all()
        
        total_amount = Decimal('0')
        for inv in invoices:
            inv_total = inv.get_total_amount_as_decimal()
            total_amount += inv_total
        
        total_count = len(invoices)
        status_breakdown = {}
        
        for inv in invoices:
            status_str = safe_string_conversion(inv.status)
            status_breakdown[status_str] = status_breakdown.get(status_str, 0) + 1
        
        return {
            'total_amount': float(total_amount),
            'total_count': total_count,
            'status_breakdown': status_breakdown,
            'invoices': [inv.to_dict() for inv in invoices]
        }

class CSVHelper:
    """Helper class for CSV operations with proper type handling"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def export_companies_csv(self) -> str:
        """Export companies to CSV format"""
        companies = self.session.query(Company).filter(
            Company.is_active == True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Company Name', 'NPWP', 'IDTKU', 'Address'])
        
        # Write data with safe string conversion
        for company in companies:
            writer.writerow([
                safe_string_conversion(company.id),
                safe_string_conversion(company.company_name),
                safe_string_conversion(company.npwp),
                safe_string_conversion(company.idtku),
                safe_string_conversion(company.address)
            ])
        
        return output.getvalue()
    
    def export_tka_workers_csv(self) -> str:
        """Export TKA workers to CSV format"""
        workers = self.session.query(TkaWorker).filter(
            TkaWorker.is_active == True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Passport', 'Division', 'Gender'])
        
        # Write data with safe string conversion
        for worker in workers:
            # Handle division field that might be None
            division_str = safe_string_conversion(worker.divisi) if safe_bool_check(worker.divisi) else ''
            
            writer.writerow([
                safe_string_conversion(worker.id),
                safe_string_conversion(worker.nama),
                safe_string_conversion(worker.passport),
                division_str,
                safe_string_conversion(worker.jenis_kelamin)
            ])
        
        return output.getvalue()
    
    def export_invoice_summary_csv(self, start_date: Optional[date] = None, 
                                  end_date: Optional[date] = None) -> str:
        """Export invoice summary to CSV format"""
        query = self.session.query(Invoice).join(Company)
        
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)
        
        invoices = query.order_by(desc(Invoice.invoice_date)).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Invoice Number', 'Company Name', 'Invoice Date', 
            'Subtotal', 'VAT Amount', 'Total Amount', 'Status'
        ])
        
        # Write data with safe conversions
        for invoice in invoices:
            writer.writerow([
                safe_string_conversion(invoice.invoice_number),
                safe_string_conversion(invoice.company.company_name),
                safe_string_conversion(invoice.invoice_date),
                safe_string_conversion(invoice.get_subtotal_as_decimal()),
                safe_string_conversion(invoice.get_vat_amount_as_decimal()),
                safe_string_conversion(invoice.get_total_amount_as_decimal()),
                safe_string_conversion(invoice.status)
            ])
        
        return output.getvalue()

if __name__ == "__main__":
    # Test business logic components
    print("Testing business logic components...")
    
    from models.database import get_db_session
    
    session = None
    try:
        session = get_db_session()
        
        # Test invoice business logic
        invoice_logic = InvoiceBusinessLogic(session)
        
        # Test VAT calculation with proper Decimal values
        vat_49 = invoice_logic.calculate_vat_amount(Decimal('163.58'), Decimal('11'))
        vat_50 = invoice_logic.calculate_vat_amount(Decimal('163.64'), Decimal('11'))
        
        print(f"VAT .49 test: {vat_49} (should be 18)")
        print(f"VAT .50 test: {vat_50} (should be 18)")
        
        # Test search helper
        search_helper = SearchHelper(session)
        companies = search_helper.search_companies("test", limit=5)
        print(f"Found {len(companies)} companies")
        
        # Test settings helper
        settings_helper = SettingsHelper(session)
        vat_rate = settings_helper.get_default_vat_percentage()
        print(f"Default VAT rate: {vat_rate}%")
        
        print("✅ Business logic test completed")
        
    except Exception as e:
        print(f"❌ Business logic test failed: {e}")
    finally:
        if session:
            session.close()