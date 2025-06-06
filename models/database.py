"""
Invoice Management System - Database Models
SQLAlchemy models for all database tables with relationships and business logic.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, Date, 
    Numeric, ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from sqlalchemy.pool import QueuePool
import logging

from config import database_config

# Setup logging
logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

class UUIDMixin:
    """Mixin for UUID primary keys"""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Check if class has __tablename__ attribute before accessing
        tablename = getattr(cls, '__tablename__', None)
        if tablename:
            uuid_column_name = f"{tablename.rstrip('s')}_uuid"
            setattr(cls, uuid_column_name, Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False))

class User(Base, TimestampMixin, UUIDMixin):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='viewer')
    full_name = Column(String(100), nullable=False)
    
    # Relationships
    created_invoices = relationship("Invoice", back_populates="creator", lazy='dynamic')
    settings_updates = relationship("Setting", back_populates="updated_by_user", lazy='dynamic')
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'viewer')", name='check_user_role'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<User(id={self.id}, username='{safe_string_conversion(self.username)}', role='{safe_string_conversion(self.role)}')>"
        except Exception:
            return f"<User(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Company(Base, TimestampMixin, UUIDMixin):
    """Company model for client companies"""
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(200), nullable=False)
    npwp = Column(String(20), nullable=False, unique=True)
    idtku = Column(String(20), nullable=False, unique=True)
    address = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    job_descriptions = relationship("JobDescription", back_populates="company", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="company")
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<Company(id={self.id}, name='{safe_string_conversion(self.company_name)}', npwp='{safe_string_conversion(self.npwp)}')>"
        except Exception:
            return f"<Company(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'company_name': self.company_name,
            'npwp': self.npwp,
            'idtku': self.idtku,
            'address': self.address,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'job_descriptions_count': len(self.job_descriptions) if self.job_descriptions else 0
        }

class TkaWorker(Base, TimestampMixin, UUIDMixin):
    """TKA Worker model for foreign workers"""
    __tablename__ = 'tka_workers'
    
    id = Column(Integer, primary_key=True)
    nama = Column(String(100), nullable=False)
    passport = Column(String(20), nullable=False, unique=True)
    divisi = Column(String(100))
    jenis_kelamin = Column(String(20), nullable=False, default='Laki-laki')
    is_active = Column(Boolean, default=True)
    
    # Relationships
    family_members = relationship("TkaFamilyMember", back_populates="tka_worker", cascade="all, delete-orphan")
    invoice_lines = relationship("InvoiceLine", back_populates="tka_worker")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("jenis_kelamin IN ('Laki-laki', 'Perempuan')", name='check_tka_gender'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<TkaWorker(id={self.id}, nama='{safe_string_conversion(self.nama)}', passport='{safe_string_conversion(self.passport)}')>"
        except Exception:
            return f"<TkaWorker(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'nama': self.nama,
            'passport': self.passport,
            'divisi': self.divisi,
            'jenis_kelamin': self.jenis_kelamin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'family_members_count': len(self.family_members) if self.family_members else 0
        }

class TkaFamilyMember(Base, TimestampMixin, UUIDMixin):
    """TKA Family Member model"""
    __tablename__ = 'tka_family_members'
    
    id = Column(Integer, primary_key=True)
    tka_id = Column(Integer, ForeignKey('tka_workers.id', ondelete='CASCADE'), nullable=False)
    nama = Column(String(100), nullable=False)
    passport = Column(String(20), nullable=False, unique=True)
    jenis_kelamin = Column(String(20), nullable=False, default='Laki-laki')
    relationship = Column(String(20), nullable=False, default='spouse')
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tka_worker = relationship("TkaWorker", back_populates="family_members")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("jenis_kelamin IN ('Laki-laki', 'Perempuan')", name='check_family_gender'),
        CheckConstraint("relationship IN ('spouse', 'parent', 'child')", name='check_family_relationship'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<TkaFamilyMember(id={self.id}, nama='{safe_string_conversion(self.nama)}', relationship='{safe_string_conversion(self.relationship)}')>"
        except Exception:
            return f"<TkaFamilyMember(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'tka_id': self.tka_id,
            'nama': self.nama,
            'passport': self.passport,
            'jenis_kelamin': self.jenis_kelamin,
            'relationship': self.relationship,
            'is_active': self.is_active,
            'tka_worker_name': self.tka_worker.nama if self.tka_worker else None
        }

class JobDescription(Base, TimestampMixin, UUIDMixin):
    """Job Description model for company-specific jobs and pricing"""
    __tablename__ = 'job_descriptions'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    job_name = Column(String(200), nullable=False)
    job_description = Column(Text, nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    company = relationship("Company", back_populates="job_descriptions")
    invoice_lines = relationship("InvoiceLine", back_populates="job_description")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("price >= 0", name='check_job_price_positive'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            price_str = safe_string_conversion(self.price)
            return f"<JobDescription(id={self.id}, name='{safe_string_conversion(self.job_name)}', price={price_str})>"
        except Exception:
            return f"<JobDescription(id={getattr(self, 'id', 'unknown')})>"
    
    def get_price_as_float(self) -> float:
        """Safe method to get price as float"""
        try:
            # Use safe conversion instead of direct float() call
            return safe_float_conversion(self.price, 0.0)
        except Exception:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'company_id': self.company_id,
            'job_name': self.job_name,
            'job_description': self.job_description,
            'price': self.get_price_as_float(),
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'company_name': self.company.company_name if self.company else None
        }

class BankAccount(Base, TimestampMixin, UUIDMixin):
    """Bank Account model for payment information"""
    __tablename__ = 'bank_accounts'
    
    id = Column(Integer, primary_key=True)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(50), nullable=False)
    account_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    invoices = relationship("Invoice", back_populates="bank_account")
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<BankAccount(id={self.id}, bank='{safe_string_conversion(self.bank_name)}', account='{safe_string_conversion(self.account_number)}')>"
        except Exception:
            return f"<BankAccount(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }

class Invoice(Base, TimestampMixin, UUIDMixin):
    """Invoice model for invoice headers"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='RESTRICT'), nullable=False)
    invoice_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    vat_percentage = Column(Numeric(5, 2), nullable=False, default=11.00)
    vat_amount = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default='draft')
    notes = Column(Text)
    bank_account_id = Column(Integer, ForeignKey('bank_accounts.id', ondelete='SET NULL'))
    printed_count = Column(Integer, default=0)
    last_printed_at = Column(DateTime)
    imported_from = Column(String(100))
    import_batch_id = Column(String(50))
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="invoices")
    creator = relationship("User", back_populates="created_invoices")
    bank_account = relationship("BankAccount", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLine.line_order")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'finalized', 'paid', 'cancelled')", name='check_invoice_status'),
        CheckConstraint("subtotal >= 0 AND vat_amount >= 0 AND total_amount >= 0", name='check_invoice_amounts_positive'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<Invoice(id={self.id}, number='{safe_string_conversion(self.invoice_number)}', total={safe_string_conversion(self.total_amount)})>"
        except Exception:
            return f"<Invoice(id={getattr(self, 'id', 'unknown')})>"
    
    def get_subtotal_as_decimal(self) -> Decimal:
        """Safe method to get subtotal as Decimal"""
        return safe_decimal_conversion(self.subtotal, Decimal('0'))
    
    def get_vat_percentage_as_decimal(self) -> Decimal:
        """Safe method to get VAT percentage as Decimal"""
        return safe_decimal_conversion(self.vat_percentage, Decimal('11.00'))
    
    def get_vat_amount_as_decimal(self) -> Decimal:
        """Safe method to get VAT amount as Decimal"""
        return safe_decimal_conversion(self.vat_amount, Decimal('0'))
    
    def get_total_amount_as_decimal(self) -> Decimal:
        """Safe method to get total amount as Decimal"""
        return safe_decimal_conversion(self.total_amount, Decimal('0'))
    
    def calculate_totals(self) -> Dict[str, Decimal]:
        """Calculate invoice totals based on line items - returns calculated values"""
        # Calculate subtotal as sum of line totals
        line_total_sum = Decimal('0')
        for line in self.lines:
            line_total = line.get_line_total_as_decimal()
            line_total_sum += line_total
        
        # Get VAT percentage safely
        vat_percentage_decimal = self.get_vat_percentage_as_decimal()
        
        # Apply special PPN rounding rule
        vat_raw = line_total_sum * vat_percentage_decimal / 100
        decimal_part = vat_raw - int(vat_raw)
        
        if abs(decimal_part - Decimal('0.49')) < Decimal('0.001'):  # .49 rule
            vat_amount_calculated = Decimal(str(int(vat_raw)))
        elif decimal_part >= Decimal('0.50'):  # .50 and above rule
            vat_amount_calculated = Decimal(str(int(vat_raw) + 1))
        else:
            vat_amount_calculated = Decimal(str(round(vat_raw, 0)))
        
        total_amount_calculated = line_total_sum + vat_amount_calculated
        
        return {
            'subtotal': line_total_sum,
            'vat_amount': vat_amount_calculated,
            'total_amount': total_amount_calculated
        }
    
    def to_dict(self) -> Dict[str, Any]:
        # Safe conversion for invoice date
        invoice_date_str = None
        if self.invoice_date is not None:
            try:
                invoice_date_str = self.invoice_date.isoformat()
            except (AttributeError, ValueError):
                invoice_date_str = str(self.invoice_date)
        
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'company_id': self.company_id,
            'invoice_date': invoice_date_str,
            'subtotal': safe_float_conversion(self.get_subtotal_as_decimal()),
            'vat_percentage': safe_float_conversion(self.get_vat_percentage_as_decimal()),
            'vat_amount': safe_float_conversion(self.get_vat_amount_as_decimal()),
            'total_amount': safe_float_conversion(self.get_total_amount_as_decimal()),
            'status': self.status,
            'notes': self.notes,
            'printed_count': safe_int_conversion(self.printed_count),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'company_name': self.company.company_name if self.company else None,
            'creator_name': self.creator.full_name if self.creator else None,
            'line_count': len(self.lines) if self.lines else 0
        }

class InvoiceLine(Base, TimestampMixin, UUIDMixin):
    """Invoice Line model for invoice line items"""
    __tablename__ = 'invoice_lines'
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    baris = Column(Integer, nullable=False)
    line_order = Column(Integer, nullable=False)
    tka_id = Column(Integer, ForeignKey('tka_workers.id', ondelete='RESTRICT'), nullable=False)
    job_description_id = Column(Integer, ForeignKey('job_descriptions.id', ondelete='RESTRICT'), nullable=False)
    custom_job_name = Column(String(200))
    custom_job_description = Column(Text)
    custom_price = Column(Numeric(15, 2))
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="lines")
    tka_worker = relationship("TkaWorker", back_populates="invoice_lines")
    job_description = relationship("JobDescription", back_populates="invoice_lines")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("unit_price >= 0 AND line_total >= 0 AND quantity > 0", name='check_line_amounts_positive'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<InvoiceLine(id={self.id}, baris={safe_string_conversion(self.baris)}, total={safe_string_conversion(self.line_total)})>"
        except Exception:
            return f"<InvoiceLine(id={getattr(self, 'id', 'unknown')})>"
    
    def get_quantity_as_int(self) -> int:
        """Safe method to get quantity as int"""
        return safe_int_conversion(self.quantity, 1)
    
    def get_unit_price_as_decimal(self) -> Decimal:
        """Safe method to get unit price as Decimal"""
        return safe_decimal_conversion(self.unit_price, Decimal('0'))
    
    def get_line_total_as_decimal(self) -> Decimal:
        """Safe method to get line total as Decimal"""
        return safe_decimal_conversion(self.line_total, Decimal('0'))
    
    def get_custom_price_as_decimal(self) -> Optional[Decimal]:
        """Safe method to get custom price as Decimal"""
        if self.custom_price is None:
            return None
        try:
            # Handle SQLAlchemy column values properly
            if hasattr(self.custom_price, '__float__'):
                return Decimal(str(float(self.custom_price)))
            elif hasattr(self.custom_price, '__str__'):
                return Decimal(str(self.custom_price))
            else:
                return Decimal(str(self.custom_price))
        except (ValueError, TypeError, AttributeError):
            return None
    
    def calculate_line_total(self) -> Decimal:
        """Calculate line total based on quantity and unit price"""
        quantity_decimal = Decimal(str(self.get_quantity_as_int()))
        unit_price_decimal = self.get_unit_price_as_decimal()
        return quantity_decimal * unit_price_decimal
    
    def to_dict(self) -> Dict[str, Any]:
        custom_price_value = self.get_custom_price_as_decimal()
        custom_price_float = safe_float_conversion(custom_price_value) if custom_price_value is not None else None
        
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'baris': self.baris,
            'line_order': self.line_order,
            'tka_id': self.tka_id,
            'job_description_id': self.job_description_id,
            'custom_job_name': self.custom_job_name,
            'custom_job_description': self.custom_job_description,
            'custom_price': custom_price_float,
            'quantity': self.get_quantity_as_int(),
            'unit_price': safe_float_conversion(self.get_unit_price_as_decimal()),
            'line_total': safe_float_conversion(self.get_line_total_as_decimal()),
            'tka_worker_name': self.tka_worker.nama if self.tka_worker else None,
            'job_name': self.custom_job_name or (self.job_description.job_name if self.job_description else None)
        }

class Setting(Base, TimestampMixin):
    """Setting model for application settings"""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(50), nullable=False, unique=True)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(20), default='string')
    description = Column(String(200))
    is_system = Column(Boolean, default=False)
    updated_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    updated_by_user = relationship("User", back_populates="settings_updates")
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<Setting(key='{safe_string_conversion(self.setting_key)}', value='{safe_string_conversion(self.setting_value)}')>"
        except Exception:
            return f"<Setting(id={getattr(self, 'id', 'unknown')})>"
    
    def get_typed_value(self):
        """Get setting value with proper type conversion"""
        # Safe check for setting_value
        if not safe_bool_check(self.setting_value):
            return None
            
        setting_value_str = safe_string_conversion(self.setting_value)
        setting_type_str = safe_string_conversion(self.setting_type, 'string')
        
        if setting_type_str == 'integer':
            try:
                return safe_int_conversion(setting_value_str, 0)
            except Exception:
                return 0
        elif setting_type_str == 'decimal':
            try:
                return safe_decimal_conversion(setting_value_str, Decimal('0'))
            except Exception:
                return Decimal('0')
        elif setting_type_str == 'boolean':
            return setting_value_str.lower() in ('true', '1', 'yes')
        else:
            return setting_value_str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'setting_type': self.setting_type,
            'description': self.description,
            'is_system': self.is_system,
            'typed_value': self.get_typed_value()
        }

class UserPreference(Base, TimestampMixin):
    """User Preference model for user-specific settings"""
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSONB)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'preference_key', name='unique_user_preference'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<UserPreference(user_id={safe_string_conversion(self.user_id)}, key='{safe_string_conversion(self.preference_key)}')>"
        except Exception:
            return f"<UserPreference(id={getattr(self, 'id', 'unknown')})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_key': self.preference_key,
            'preference_value': self.preference_value
        }

class InvoiceNumberSequence(Base, TimestampMixin):
    """Invoice Number Sequence model for auto-incrementing invoice numbers"""
    __tablename__ = 'invoice_number_sequences'
    
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    current_number = Column(Integer, nullable=False, default=0)
    prefix = Column(String(10), default='')
    suffix = Column(String(10), default='')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('year', 'month', name='unique_year_month'),
        CheckConstraint("month >= 1 AND month <= 12 AND current_number >= 0", name='check_sequence_values'),
    )
    
    def __repr__(self):
        # Safe string representation to avoid Column callable issues
        try:
            return f"<InvoiceNumberSequence(year={safe_string_conversion(self.year)}, month={safe_string_conversion(self.month)}, current={safe_string_conversion(self.current_number)})>"
        except Exception:
            return f"<InvoiceNumberSequence(id={getattr(self, 'id', 'unknown')})>"
    
    def get_current_number_as_int(self) -> int:
        """Safe method to get current number as int"""
        return safe_int_conversion(self.current_number, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'current_number': self.get_current_number_as_int(),
            'prefix': safe_string_conversion(self.prefix),
            'suffix': safe_string_conversion(self.suffix)
        }

# Helper functions for safe value access and conversion
def safe_get_column_value(instance: Any, column_name: str, default: Any = None) -> Any:
    """Safely get column value from SQLAlchemy instance"""
    try:
        value = getattr(instance, column_name, default)
        return value if value is not None else default
    except Exception:
        return default

def safe_decimal_conversion(value: Any, default: Decimal = Decimal('0')) -> Decimal:
    """Safely convert value to Decimal"""
    if value is None:
        return default
    try:
        # Handle SQLAlchemy column values properly
        if hasattr(value, '__float__'):
            # Try to get the actual value if it's a SQLAlchemy result
            return Decimal(str(float(value)))
        elif hasattr(value, '__str__'):
            return Decimal(str(value))
        else:
            return Decimal(str(value))
    except (ValueError, TypeError, AttributeError):
        return default

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    if value is None:
        return default
    try:
        # Handle SQLAlchemy column values properly
        if hasattr(value, '__float__'):
            return float(value)
        elif isinstance(value, (int, float, Decimal)):
            return float(value)
        else:
            return float(str(value))
    except (ValueError, TypeError, AttributeError):
        return default

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    if value is None:
        return default
    try:
        # Handle SQLAlchemy column values properly
        if hasattr(value, '__int__'):
            return int(value)
        elif isinstance(value, (int, float, str)):
            return int(float(value))  # Convert via float to handle decimal strings
        else:
            return int(str(value))
    except (ValueError, TypeError, AttributeError):
        return default

def safe_string_conversion(value: Any, default: str = "") -> str:
    """Safely convert value to string"""
    if value is None:
        return default
    try:
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return default

def safe_bool_check(value: Any) -> bool:
    """Safely check if value is truthy without triggering SQLAlchemy __bool__ issues"""
    if value is None:
        return False
    try:
        # For SQLAlchemy columns, check if it's not None instead of boolean conversion
        if hasattr(value, '__table__') or hasattr(value, '_sa_class_manager'):
            return value is not None
        # For regular values, use standard truthiness
        return bool(value)
    except Exception:
        return False

# Database connection and session management
class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection"""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                database_config.url,
                poolclass=QueuePool,
                pool_size=database_config.pool_size,
                max_overflow=database_config.max_overflow,
                pool_timeout=database_config.pool_timeout,
                pool_recycle=database_config.pool_recycle,
                echo=False  # Set to True for SQL debugging
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        try:
            if self.SessionLocal is None:
                raise RuntimeError("Database not initialized")
            return self.SessionLocal()
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def close_session(self, session: Session):
        """Close database session"""
        try:
            if session:
                session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        session = None
        try:
            session = self.get_session()
            # Use text() for raw SQL to avoid type issues
            session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        finally:
            if session:
                self.close_session(session)

# Global database manager instance
db_manager = DatabaseManager()

def get_db_session() -> Session:
    """Get a new database session"""
    return db_manager.get_session()

def init_database():
    """Initialize database tables"""
    db_manager.create_tables()

if __name__ == "__main__":
    # Test database connection and create tables
    try:
        if db_manager.test_connection():
            print("✅ Database connection successful")
            db_manager.create_tables()
            print("✅ Database tables created")
        else:
            print("❌ Database connection failed")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")