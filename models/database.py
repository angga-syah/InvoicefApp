"""
Invoice Management System - Database Models
SQLAlchemy models for all database tables with relationships and business logic.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, Date, 
    Numeric, ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
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
        # Add UUID column for each model
        uuid_column_name = f"{cls.__tablename__.rstrip('s')}_uuid"
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
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
    
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
        return f"<Company(id={self.id}, name='{self.company_name}', npwp='{self.npwp}')>"
    
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
        return f"<TkaWorker(id={self.id}, nama='{self.nama}', passport='{self.passport}')>"
    
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
        return f"<TkaFamilyMember(id={self.id}, nama='{self.nama}', relationship='{self.relationship}')>"
    
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
        return f"<JobDescription(id={self.id}, name='{self.job_name}', price={self.price})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'company_id': self.company_id,
            'job_name': self.job_name,
            'job_description': self.job_description,
            'price': float(self.price),
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
        return f"<BankAccount(id={self.id}, bank='{self.bank_name}', account='{self.account_number}')>"
    
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
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', total={self.total_amount})>"
    
    def calculate_totals(self):
        """Calculate invoice totals based on line items"""
        self.subtotal = sum(line.line_total for line in self.lines)
        
        # Apply special PPN rounding rule
        vat_raw = self.subtotal * self.vat_percentage / 100
        decimal_part = vat_raw - int(vat_raw)
        
        if abs(decimal_part - 0.49) < 0.001:  # .49 rule
            self.vat_amount = int(vat_raw)
        elif decimal_part >= 0.50:  # .50 and above rule
            self.vat_amount = int(vat_raw) + 1
        else:
            self.vat_amount = round(vat_raw, 0)
        
        self.total_amount = self.subtotal + self.vat_amount
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'company_id': self.company_id,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'subtotal': float(self.subtotal),
            'vat_percentage': float(self.vat_percentage),
            'vat_amount': float(self.vat_amount),
            'total_amount': float(self.total_amount),
            'status': self.status,
            'notes': self.notes,
            'printed_count': self.printed_count,
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
        return f"<InvoiceLine(id={self.id}, baris={self.baris}, total={self.line_total})>"
    
    def calculate_line_total(self):
        """Calculate line total based on quantity and unit price"""
        self.line_total = self.quantity * self.unit_price
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'baris': self.baris,
            'line_order': self.line_order,
            'tka_id': self.tka_id,
            'job_description_id': self.job_description_id,
            'custom_job_name': self.custom_job_name,
            'custom_job_description': self.custom_job_description,
            'custom_price': float(self.custom_price) if self.custom_price else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'line_total': float(self.line_total),
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
        return f"<Setting(key='{self.setting_key}', value='{self.setting_value}')>"
    
    def get_typed_value(self):
        """Get setting value with proper type conversion"""
        if self.setting_type == 'integer':
            return int(self.setting_value)
        elif self.setting_type == 'decimal':
            return Decimal(self.setting_value)
        elif self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        else:
            return self.setting_value
    
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
        return f"<UserPreference(user_id={self.user_id}, key='{self.preference_key}')>"
    
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
        return f"<InvoiceNumberSequence(year={self.year}, month={self.month}, current={self.current_number})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'current_number': self.current_number,
            'prefix': self.prefix,
            'suffix': self.suffix
        }

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
            return self.SessionLocal()
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def close_session(self, session: Session):
        """Close database session"""
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            session = self.get_session()
            session.execute("SELECT 1")
            session.close()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

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