"""
Invoice Management System - Core Invoice Service
Comprehensive service for all invoice-related operations including creation, 
editing, calculations, and business logic implementation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import logging

from models.database import (
    Invoice, InvoiceLine, Company, TkaWorker, TkaFamilyMember, 
    JobDescription, BankAccount, User, get_db_session
)
from models.business import (
    InvoiceBusinessLogic, DataHelper, ValidationHelper, 
    SettingsHelper, BusinessError
)
from services.cache_service import cached, query_cache, invalidate_cache
from utils.validators import (
    validate_invoice_data, validate_invoice_line_data, ValidationResult
)
from utils.formatters import format_currency_idr, format_date_short
from utils.helpers import safe_decimal

logger = logging.getLogger(__name__)

class InvoiceService:
    """Core service for invoice operations"""
    
    def __init__(self, session: Session = None):
        self.session = session or get_db_session()
        self.invoice_logic = InvoiceBusinessLogic(self.session)
        self.data_helper = DataHelper(self.session)
        self.validation_helper = ValidationHelper(self.session)
        self.settings_helper = SettingsHelper(self.session)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
    
    # ========== INVOICE CREATION ==========
    
    def create_invoice(self, invoice_data: Dict[str, Any], line_items: List[Dict[str, Any]], 
                      user_id: int) -> Tuple[Invoice, ValidationResult]:
        """
        Create new invoice with line items
        
        Args:
            invoice_data: Invoice header data
            line_items: List of invoice line items
            user_id: User creating the invoice
            
        Returns:
            Tuple of (created_invoice, validation_result)
        """
        validation_result = ValidationResult()
        
        try:
            # Validate invoice data
            invoice_validation = validate_invoice_data(invoice_data)
            if not invoice_validation.is_valid:
                validation_result.errors.extend(invoice_validation.errors)
                return None, validation_result
            
            # Validate line items
            if not line_items:
                validation_result.add_error("Invoice must have at least one line item", "lines")
                return None, validation_result
            
            for i, line_data in enumerate(line_items):
                line_validation = validate_invoice_line_data(line_data)
                if not line_validation.is_valid:
                    for error in line_validation.errors:
                        validation_result.add_error(
                            f"Line {i+1}: {error['message']}", 
                            f"line_{i}_{error['field']}"
                        )
            
            if not validation_result.is_valid:
                return None, validation_result
            
            # Create invoice
            invoice = Invoice(
                company_id=invoice_data['company_id'],
                invoice_date=invoice_data.get('invoice_date', date.today()),
                vat_percentage=invoice_data.get('vat_percentage', self.settings_helper.get_default_vat_percentage()),
                status=invoice_data.get('status', 'draft'),
                notes=invoice_data.get('notes', ''),
                bank_account_id=invoice_data.get('bank_account_id'),
                created_by=user_id
            )
            
            # Generate invoice number if not provided
            if not invoice_data.get('invoice_number'):
                invoice.invoice_number = self.invoice_logic.generate_invoice_number(invoice.invoice_date)
            else:
                invoice.invoice_number = invoice_data['invoice_number']
            
            self.session.add(invoice)
            self.session.flush()  # Get invoice ID
            
            # Add line items
            for i, line_data in enumerate(line_items):
                line = self._create_invoice_line(invoice.id, line_data, i + 1)
                self.session.add(line)
            
            # Calculate totals
            self.session.flush()  # Ensure lines are saved
            self.session.refresh(invoice)  # Reload with lines
            self.invoice_logic.update_invoice_totals(invoice)
            
            self.session.commit()
            
            # Invalidate relevant caches
            invalidate_cache("invoices:*")
            invalidate_cache("invoice_stats:*")
            
            logger.info(f"Created invoice {invoice.invoice_number} for company {invoice.company_id}")
            return invoice, validation_result
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating invoice: {e}")
            validation_result.add_error(f"Failed to create invoice: {str(e)}", "general")
            return None, validation_result
    
    def _create_invoice_line(self, invoice_id: int, line_data: Dict[str, Any], line_order: int) -> InvoiceLine:
        """Create individual invoice line"""
        # Get job description for default values
        job_description = self.session.query(JobDescription).get(line_data['job_description_id'])
        
        # Calculate unit price (use custom price if provided, otherwise job price)
        unit_price = safe_decimal(line_data.get('custom_price') or job_description.price)
        quantity = int(line_data.get('quantity', 1))
        line_total = unit_price * quantity
        
        return InvoiceLine(
            invoice_id=invoice_id,
            baris=line_data.get('baris', line_order),
            line_order=line_order,
            tka_id=line_data['tka_id'],
            job_description_id=line_data['job_description_id'],
            custom_job_name=line_data.get('custom_job_name'),
            custom_job_description=line_data.get('custom_job_description'),
            custom_price=line_data.get('custom_price'),
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total
        )
    
    # ========== INVOICE EDITING ==========
    
    def update_invoice(self, invoice_id: int, invoice_data: Dict[str, Any], 
                      line_items: List[Dict[str, Any]] = None) -> Tuple[Invoice, ValidationResult]:
        """
        Update existing invoice
        
        Args:
            invoice_id: ID of invoice to update
            invoice_data: Updated invoice data
            line_items: Updated line items (optional)
            
        Returns:
            Tuple of (updated_invoice, validation_result)
        """
        validation_result = ValidationResult()
        
        try:
            invoice = self.session.query(Invoice).get(invoice_id)
            if not invoice:
                validation_result.add_error("Invoice not found", "invoice_id")
                return None, validation_result
            
            # Check if invoice can be edited
            if not self.invoice_logic.can_edit_invoice(invoice):
                validation_result.add_error(
                    f"Cannot edit invoice with status '{invoice.status}'", 
                    "status"
                )
                return None, validation_result
            
            # Validate invoice data
            invoice_validation = validate_invoice_data(invoice_data)
            if not invoice_validation.is_valid:
                validation_result.errors.extend(invoice_validation.errors)
                return None, validation_result
            
            # Update invoice fields
            for field, value in invoice_data.items():
                if hasattr(invoice, field) and field not in ['id', 'created_at', 'created_by']:
                    setattr(invoice, field, value)
            
            # Update line items if provided
            if line_items is not None:
                # Validate line items
                for i, line_data in enumerate(line_items):
                    line_validation = validate_invoice_line_data(line_data)
                    if not line_validation.is_valid:
                        for error in line_validation.errors:
                            validation_result.add_error(
                                f"Line {i+1}: {error['message']}", 
                                f"line_{i}_{error['field']}"
                            )
                
                if not validation_result.is_valid:
                    return None, validation_result
                
                # Remove existing lines
                self.session.query(InvoiceLine).filter(
                    InvoiceLine.invoice_id == invoice_id
                ).delete()
                
                # Add new lines
                for i, line_data in enumerate(line_items):
                    line = self._create_invoice_line(invoice_id, line_data, i + 1)
                    self.session.add(line)
            
            # Recalculate totals
            self.session.flush()
            self.session.refresh(invoice)
            self.invoice_logic.update_invoice_totals(invoice)
            
            self.session.commit()
            
            # Invalidate caches
            invalidate_cache(f"invoice:{invoice_id}")
            invalidate_cache("invoices:*")
            
            logger.info(f"Updated invoice {invoice.invoice_number}")
            return invoice, validation_result
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating invoice {invoice_id}: {e}")
            validation_result.add_error(f"Failed to update invoice: {str(e)}", "general")
            return None, validation_result
    
    def update_invoice_status(self, invoice_id: int, new_status: str, user_id: int) -> Tuple[Invoice, ValidationResult]:
        """Update invoice status"""
        validation_result = ValidationResult()
        
        try:
            invoice = self.session.query(Invoice).get(invoice_id)
            if not invoice:
                validation_result.add_error("Invoice not found", "invoice_id")
                return None, validation_result
            
            # Validate status transition
            if not self.invoice_logic.validate_invoice_transition(invoice.status, new_status):
                validation_result.add_error(
                    f"Cannot change status from '{invoice.status}' to '{new_status}'", 
                    "status"
                )
                return None, validation_result
            
            old_status = invoice.status
            invoice.status = new_status
            
            self.session.commit()
            
            # Invalidate caches
            invalidate_cache(f"invoice:{invoice_id}")
            invalidate_cache("invoices:*")
            
            logger.info(f"Changed invoice {invoice.invoice_number} status from {old_status} to {new_status}")
            return invoice, validation_result
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating invoice status: {e}")
            validation_result.add_error(f"Failed to update status: {str(e)}", "general")
            return None, validation_result
    
    # ========== INVOICE DELETION ==========
    
    def delete_invoice(self, invoice_id: int, user_id: int) -> ValidationResult:
        """Delete invoice"""
        validation_result = ValidationResult()
        
        try:
            invoice = self.session.query(Invoice).get(invoice_id)
            if not invoice:
                validation_result.add_error("Invoice not found", "invoice_id")
                return validation_result
            
            # Check if invoice can be deleted
            if not self.invoice_logic.can_delete_invoice(invoice):
                validation_result.add_error(
                    f"Cannot delete invoice with status '{invoice.status}'", 
                    "status"
                )
                return validation_result
            
            invoice_number = invoice.invoice_number
            
            # Delete invoice (cascade will delete lines)
            self.session.delete(invoice)
            self.session.commit()
            
            # Invalidate caches
            invalidate_cache(f"invoice:{invoice_id}")
            invalidate_cache("invoices:*")
            
            logger.info(f"Deleted invoice {invoice_number}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting invoice {invoice_id}: {e}")
            validation_result.add_error(f"Failed to delete invoice: {str(e)}", "general")
        
        return validation_result
    
    # ========== INVOICE RETRIEVAL ==========
    
    @cached("invoice", ttl=1800)
    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID"""
        return self.session.query(Invoice).get(invoice_id)
    
    def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by number"""
        return self.session.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()
    
    @cached("invoices_list", ttl=900)
    def get_invoices_list(self, page: int = 1, per_page: int = 50, 
                         filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get paginated invoices list with filters"""
        query = self.session.query(Invoice).join(Company)
        
        # Apply filters
        if filters:
            if filters.get('company_id'):
                query = query.filter(Invoice.company_id == filters['company_id'])
            
            if filters.get('status'):
                query = query.filter(Invoice.status == filters['status'])
            
            if filters.get('start_date'):
                query = query.filter(Invoice.invoice_date >= filters['start_date'])
            
            if filters.get('end_date'):
                query = query.filter(Invoice.invoice_date <= filters['end_date'])
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Invoice.invoice_number.ilike(search_term),
                        Company.company_name.ilike(search_term),
                        Company.npwp.like(search_term)
                    )
                )
        
        # Count total
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        invoices = query.order_by(
            desc(Invoice.invoice_date), desc(Invoice.created_at)
        ).offset(offset).limit(per_page).all()
        
        return {
            'invoices': [invoice.to_dict() for invoice in invoices],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    def get_recent_invoices(self, limit: int = 10) -> List[Invoice]:
        """Get recent invoices"""
        return self.session.query(Invoice).order_by(
            desc(Invoice.created_at)
        ).limit(limit).all()
    
    # ========== INVOICE OPERATIONS ==========
    
    def clone_invoice(self, invoice_id: int, user_id: int, 
                     new_invoice_date: date = None) -> Tuple[Invoice, ValidationResult]:
        """Clone existing invoice"""
        validation_result = ValidationResult()
        
        try:
            original = self.session.query(Invoice).get(invoice_id)
            if not original:
                validation_result.add_error("Original invoice not found", "invoice_id")
                return None, validation_result
            
            # Prepare invoice data
            invoice_data = {
                'company_id': original.company_id,
                'invoice_date': new_invoice_date or date.today(),
                'vat_percentage': original.vat_percentage,
                'notes': original.notes,
                'bank_account_id': original.bank_account_id
            }
            
            # Prepare line items
            line_items = []
            for line in original.lines:
                line_data = {
                    'tka_id': line.tka_id,
                    'job_description_id': line.job_description_id,
                    'custom_job_name': line.custom_job_name,
                    'custom_job_description': line.custom_job_description,
                    'custom_price': line.custom_price,
                    'quantity': line.quantity,
                    'baris': line.baris
                }
                line_items.append(line_data)
            
            # Create new invoice
            new_invoice, result = self.create_invoice(invoice_data, line_items, user_id)
            
            if result.is_valid:
                logger.info(f"Cloned invoice {original.invoice_number} to {new_invoice.invoice_number}")
            
            return new_invoice, result
            
        except Exception as e:
            logger.error(f"Error cloning invoice {invoice_id}: {e}")
            validation_result.add_error(f"Failed to clone invoice: {str(e)}", "general")
            return None, validation_result
    
    def mark_invoice_printed(self, invoice_id: int) -> None:
        """Mark invoice as printed"""
        try:
            invoice = self.session.query(Invoice).get(invoice_id)
            if invoice:
                invoice.printed_count += 1
                invoice.last_printed_at = datetime.now()
                self.session.commit()
                
                # Invalidate cache
                invalidate_cache(f"invoice:{invoice_id}")
                
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error marking invoice as printed: {e}")
    
    # ========== BUSINESS CALCULATIONS ==========
    
    def calculate_invoice_preview(self, company_id: int, line_items: List[Dict[str, Any]], 
                                vat_percentage: Decimal = None) -> Dict[str, Any]:
        """Calculate invoice totals without saving"""
        if vat_percentage is None:
            vat_percentage = self.settings_helper.get_default_vat_percentage()
        
        subtotal = Decimal('0')
        lines_preview = []
        
        for line_data in line_items:
            # Get job description
            job = self.session.query(JobDescription).get(line_data['job_description_id'])
            if not job:
                continue
            
            # Calculate line total
            unit_price = safe_decimal(line_data.get('custom_price') or job.price)
            quantity = int(line_data.get('quantity', 1))
            line_total = unit_price * quantity
            
            subtotal += line_total
            
            lines_preview.append({
                'unit_price': unit_price,
                'quantity': quantity,
                'line_total': line_total,
                'job_name': line_data.get('custom_job_name') or job.job_name
            })
        
        # Calculate VAT and total
        vat_amount = self.invoice_logic.calculate_vat_amount(subtotal, vat_percentage)
        total_amount = subtotal + vat_amount
        
        return {
            'subtotal': subtotal,
            'vat_percentage': vat_percentage,
            'vat_amount': vat_amount,
            'total_amount': total_amount,
            'lines': lines_preview,
            'formatted': {
                'subtotal': format_currency_idr(subtotal),
                'vat_amount': format_currency_idr(vat_amount),
                'total_amount': format_currency_idr(total_amount)
            }
        }
    
    # ========== STATISTICS ==========
    
    @cached("invoice_stats", ttl=3600)
    def get_invoice_statistics(self) -> Dict[str, Any]:
        """Get invoice statistics"""
        # Status counts
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
        
        # Recent activity
        recent_count = self.session.query(Invoice).filter(
            Invoice.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        
        return {
            'status_counts': dict(status_counts),
            'status_amounts': {status: float(amount or 0) for status, amount in status_amounts},
            'monthly_totals': {int(month): float(total or 0) for month, total in monthly_totals},
            'recent_count': recent_count,
            'total_invoices': sum(count for _, count in status_counts)
        }
    
    # ========== SEARCH ==========
    
    def search_invoices(self, query: str, limit: int = 50) -> List[Invoice]:
        """Search invoices"""
        if not query:
            return self.get_recent_invoices(limit)
        
        return self.session.query(Invoice).join(Company).filter(
            or_(
                Invoice.invoice_number.ilike(f'%{query}%'),
                Company.company_name.ilike(f'%{query}%'),
                Company.npwp.like(f'%{query}%')
            )
        ).order_by(
            desc(Invoice.invoice_date), desc(Invoice.created_at)
        ).limit(limit).all()

# Utility functions for external use
def create_invoice_service() -> InvoiceService:
    """Create new invoice service instance"""
    return InvoiceService()

def get_invoice_quick_info(invoice_id: int) -> Optional[Dict[str, Any]]:
    """Get quick invoice information"""
    with create_invoice_service() as service:
        invoice = service.get_invoice(invoice_id)
        if invoice:
            return {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'company_name': invoice.company.company_name,
                'total_amount': float(invoice.total_amount),
                'status': invoice.status,
                'invoice_date': format_date_short(invoice.invoice_date),
                'formatted_total': format_currency_idr(invoice.total_amount)
            }
        return None

if __name__ == "__main__":
    # Test invoice service
    print("Testing invoice service...")
    
    try:
        with create_invoice_service() as service:
            # Test get recent invoices
            recent = service.get_recent_invoices(5)
            print(f"Found {len(recent)} recent invoices")
            
            # Test statistics
            stats = service.get_invoice_statistics()
            print(f"Invoice statistics: {stats}")
            
            print("✅ Invoice service test completed")
            
    except Exception as e:
        print(f"❌ Invoice service test failed: {e}")