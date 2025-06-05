"""
Invoice Management System - Dialog Windows and Forms
Comprehensive dialog windows for data entry, editing, and user interactions
with modern UI design and validation.
"""

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QCheckBox, QGroupBox, QTabWidget, QWidget, QScrollArea,
    QDialogButtonBox, QMessageBox, QFileDialog, QProgressDialog,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

from models.database import (
    Company, TkaWorker, TkaFamilyMember, JobDescription, 
    Invoice, InvoiceLine, User, BankAccount
)
from services.invoice_service import InvoiceService
from models.business import DataHelper, ValidationHelper
from ui.widgets import (
    SmartSearchWidget, CurrencyInputWidget, AutoCompleteComboBox,
    NumericInputWidget, StatusIndicator, ModernButton, LoadingSpinner,
    DataGridWidget, create_modern_button
)
from utils.validators import (
    validate_company_data, validate_tka_worker_data, 
    validate_job_description_data, ValidationResult
)
from utils.formatters import format_currency_idr, format_npwp_display
from utils.helpers import safe_decimal, normalize_name

logger = logging.getLogger(__name__)

class BaseDialog(QDialog):
    """Base dialog with common functionality"""
    
    def __init__(self, title: str = "Dialog", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(600, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup base UI structure"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(16)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.main_layout.addWidget(self.content_widget)
        
        # Button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)
    
    def add_content_widget(self, widget: QWidget):
        """Add widget to content area"""
        self.content_layout.addWidget(widget)
    
    def set_ok_button_text(self, text: str):
        """Set OK button text"""
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText(text)
    
    def enable_ok_button(self, enabled: bool):
        """Enable/disable OK button"""
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(enabled)

class LoginDialog(BaseDialog):
    """User login dialog"""
    
    def __init__(self, parent=None):
        super().__init__("Login - Invoice Management System", parent)
        self.resize(400, 300)
        self._setup_login_ui()
        self._setup_connections()
        self.credentials = None
    
    def _setup_login_ui(self):
        """Setup login UI"""
        # Logo/Title area
        title_label = QLabel("Invoice Management System")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin: 20px;")
        
        subtitle_label = QLabel("Please sign in to continue")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        
        # Login form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        form_layout.addRow("Username:", self.username_input)
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Remember login
        self.remember_checkbox = QCheckBox("Remember me on this computer")
        form_layout.addRow("", self.remember_checkbox)
        
        # Add to content
        self.add_content_widget(title_label)
        self.add_content_widget(subtitle_label)
        self.add_content_widget(form_widget)
        
        # Update button text
        self.set_ok_button_text("Sign In")
        
        # Set focus
        self.username_input.setFocus()
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.username_input.textChanged.connect(self._validate_form)
        self.password_input.textChanged.connect(self._validate_form)
        self.password_input.returnPressed.connect(self.accept)
        
        # Initial validation
        self._validate_form()
    
    def _validate_form(self):
        """Validate login form"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        is_valid = bool(username and password)
        self.enable_ok_button(is_valid)
    
    def accept(self):
        """Handle login acceptance"""
        self.credentials = {
            'username': self.username_input.text().strip(),
            'password': self.password_input.text(),
            'remember': self.remember_checkbox.isChecked()
        }
        super().accept()
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Get login credentials"""
        return self.credentials

class CompanyDialog(BaseDialog):
    """Company create/edit dialog"""
    
    def __init__(self, company: Company = None, parent=None):
        self.company = company
        self.is_edit_mode = company is not None
        title = "Edit Company" if self.is_edit_mode else "Add New Company"
        super().__init__(title, parent)
        self._setup_company_ui()
        self._setup_connections()
        if self.is_edit_mode:
            self._load_company_data()
    
    def _setup_company_ui(self):
        """Setup company form UI"""
        # Main form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        
        # Company name
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Enter company name")
        form_layout.addRow("Company Name *:", self.company_name_input)
        
        # NPWP
        self.npwp_input = QLineEdit()
        self.npwp_input.setPlaceholderText("XX.XXX.XXX.X-XXX.XXX")
        self.npwp_input.setMaxLength(20)
        form_layout.addRow("NPWP *:", self.npwp_input)
        
        # IDTKU
        self.idtku_input = QLineEdit()
        self.idtku_input.setPlaceholderText("Enter IDTKU")
        form_layout.addRow("IDTKU *:", self.idtku_input)
        
        # Address
        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("Enter complete address")
        self.address_input.setMaximumHeight(100)
        form_layout.addRow("Address *:", self.address_input)
        
        # Status
        self.status_checkbox = QCheckBox("Company is active")
        self.status_checkbox.setChecked(True)
        form_layout.addRow("Status:", self.status_checkbox)
        
        self.add_content_widget(form_widget)
        
        # Validation info
        info_label = QLabel("* Required fields")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        self.add_content_widget(info_label)
        
        # Update button text
        self.set_ok_button_text("Update Company" if self.is_edit_mode else "Create Company")
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Validation on text changes
        self.company_name_input.textChanged.connect(self._validate_form)
        self.npwp_input.textChanged.connect(self._validate_form)
        self.idtku_input.textChanged.connect(self._validate_form)
        self.address_input.textChanged.connect(self._validate_form)
        
        # NPWP formatting
        self.npwp_input.textChanged.connect(self._format_npwp)
        
        # Initial validation
        self._validate_form()
    
    def _format_npwp(self, text: str):
        """Auto-format NPWP input"""
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, text))
        
        # Format as XX.XXX.XXX.X-XXX.XXX
        if len(digits) <= 15:
            formatted = digits
            if len(digits) > 2:
                formatted = f"{digits[:2]}.{digits[2:]}"
            if len(digits) > 5:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:]}"
            if len(digits) > 8:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8:]}"
            if len(digits) > 9:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:]}"
            if len(digits) > 12:
                formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:]}"
            
            # Update input without triggering signal
            self.npwp_input.blockSignals(True)
            self.npwp_input.setText(formatted)
            self.npwp_input.blockSignals(False)
    
    def _validate_form(self):
        """Validate company form"""
        is_valid = (
            bool(self.company_name_input.text().strip()) and
            bool(self.npwp_input.text().strip()) and
            bool(self.idtku_input.text().strip()) and
            bool(self.address_input.toPlainText().strip())
        )
        self.enable_ok_button(is_valid)
    
    def _load_company_data(self):
        """Load existing company data"""
        if self.company:
            self.company_name_input.setText(self.company.company_name)
            self.npwp_input.setText(self.company.npwp)
            self.idtku_input.setText(self.company.idtku)
            self.address_input.setPlainText(self.company.address)
            self.status_checkbox.setChecked(self.company.is_active)
    
    def get_company_data(self) -> Dict[str, Any]:
        """Get company data from form"""
        return {
            'company_name': self.company_name_input.text().strip(),
            'npwp': self.npwp_input.text().strip(),
            'idtku': self.idtku_input.text().strip(),
            'address': self.address_input.toPlainText().strip(),
            'is_active': self.status_checkbox.isChecked()
        }
    
    def accept(self):
        """Validate and accept"""
        company_data = self.get_company_data()
        validation = validate_company_data(company_data)
        
        if not validation.is_valid:
            error_msg = "Please fix the following errors:\n\n"
            error_msg += "\n".join([error['message'] for error in validation.errors])
            QMessageBox.warning(self, "Validation Error", error_msg)
            return
        
        super().accept()

class TkaWorkerDialog(BaseDialog):
    """TKA Worker create/edit dialog"""
    
    def __init__(self, tka_worker: TkaWorker = None, parent=None):
        self.tka_worker = tka_worker
        self.is_edit_mode = tka_worker is not None
        title = "Edit TKA Worker" if self.is_edit_mode else "Add New TKA Worker"
        super().__init__(title, parent)
        self._setup_tka_ui()
        self._setup_connections()
        if self.is_edit_mode:
            self._load_tka_data()
    
    def _setup_tka_ui(self):
        """Setup TKA worker form UI"""
        # Create tabs for main info and family
        tab_widget = QTabWidget()
        
        # Main info tab
        main_tab = QWidget()
        main_layout = QFormLayout(main_tab)
        main_layout.setSpacing(12)
        
        # Name
        self.nama_input = QLineEdit()
        self.nama_input.setPlaceholderText("Enter full name")
        main_layout.addRow("Full Name *:", self.nama_input)
        
        # Passport
        self.passport_input = QLineEdit()
        self.passport_input.setPlaceholderText("Enter passport number")
        self.passport_input.setMaxLength(20)
        main_layout.addRow("Passport Number *:", self.passport_input)
        
        # Gender
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Laki-laki", "Perempuan"])
        main_layout.addRow("Gender *:", self.gender_combo)
        
        # Division
        self.divisi_input = QLineEdit()
        self.divisi_input.setPlaceholderText("Enter division/department")
        main_layout.addRow("Division:", self.divisi_input)
        
        # Status
        self.status_checkbox = QCheckBox("Worker is active")
        self.status_checkbox.setChecked(True)
        main_layout.addRow("Status:", self.status_checkbox)
        
        tab_widget.addTab(main_tab, "Main Information")
        
        # Family members tab (for edit mode)
        if self.is_edit_mode:
            family_tab = self._create_family_tab()
            tab_widget.addTab(family_tab, "Family Members")
        
        self.add_content_widget(tab_widget)
        
        # Validation info
        info_label = QLabel("* Required fields")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        self.add_content_widget(info_label)
        
        # Update button text
        self.set_ok_button_text("Update Worker" if self.is_edit_mode else "Create Worker")
    
    def _create_family_tab(self) -> QWidget:
        """Create family members tab"""
        family_widget = QWidget()
        layout = QVBoxLayout(family_widget)
        
        # Family members table
        self.family_table = DataGridWidget()
        layout.addWidget(self.family_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_family_btn = create_modern_button("Add Family Member", "success")
        add_family_btn.clicked.connect(self._add_family_member)
        
        edit_family_btn = create_modern_button("Edit Selected", "primary")
        edit_family_btn.clicked.connect(self._edit_family_member)
        
        remove_family_btn = create_modern_button("Remove Selected", "danger")
        remove_family_btn.clicked.connect(self._remove_family_member)
        
        button_layout.addWidget(add_family_btn)
        button_layout.addWidget(edit_family_btn)
        button_layout.addWidget(remove_family_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return family_widget
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.nama_input.textChanged.connect(self._validate_form)
        self.passport_input.textChanged.connect(self._validate_form)
        
        # Name formatting
        self.nama_input.textChanged.connect(self._format_name)
        
        # Initial validation
        self._validate_form()
    
    def _format_name(self, text: str):
        """Auto-format name input"""
        formatted = normalize_name(text)
        if formatted != text:
            self.nama_input.blockSignals(True)
            self.nama_input.setText(formatted)
            self.nama_input.blockSignals(False)
    
    def _validate_form(self):
        """Validate TKA form"""
        is_valid = (
            bool(self.nama_input.text().strip()) and
            bool(self.passport_input.text().strip())
        )
        self.enable_ok_button(is_valid)
    
    def _load_tka_data(self):
        """Load existing TKA data"""
        if self.tka_worker:
            self.nama_input.setText(self.tka_worker.nama)
            self.passport_input.setText(self.tka_worker.passport)
            self.gender_combo.setCurrentText(self.tka_worker.jenis_kelamin)
            self.divisi_input.setText(self.tka_worker.divisi or "")
            self.status_checkbox.setChecked(self.tka_worker.is_active)
            
            # Load family members
            self._load_family_members()
    
    def _load_family_members(self):
        """Load family members data"""
        if not self.tka_worker or not hasattr(self, 'family_table'):
            return
        
        family_data = []
        for family_member in self.tka_worker.family_members:
            family_data.append({
                'id': family_member.id,
                'nama': family_member.nama,
                'passport': family_member.passport,
                'jenis_kelamin': family_member.jenis_kelamin,
                'relationship': family_member.relationship,
                'is_active': family_member.is_active
            })
        
        columns = [
            {'key': 'nama', 'title': 'Name', 'type': 'text'},
            {'key': 'passport', 'title': 'Passport', 'type': 'text'},
            {'key': 'jenis_kelamin', 'title': 'Gender', 'type': 'text'},
            {'key': 'relationship', 'title': 'Relationship', 'type': 'text'},
            {'key': 'is_active', 'title': 'Status', 'type': 'status'}
        ]
        
        self.family_table.set_data(family_data, columns)
    
    def _add_family_member(self):
        """Add new family member"""
        # This would open a family member dialog
        QMessageBox.information(self, "Info", "Family member management will be implemented")
    
    def _edit_family_member(self):
        """Edit selected family member"""
        selected = self.family_table.get_selected_data()
        if selected:
            QMessageBox.information(self, "Info", f"Edit family member: {selected['nama']}")
    
    def _remove_family_member(self):
        """Remove selected family member"""
        selected = self.family_table.get_selected_data()
        if selected:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to remove {selected['nama']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, "Info", "Family member removal will be implemented")
    
    def get_tka_data(self) -> Dict[str, Any]:
        """Get TKA data from form"""
        return {
            'nama': self.nama_input.text().strip(),
            'passport': self.passport_input.text().strip(),
            'jenis_kelamin': self.gender_combo.currentText(),
            'divisi': self.divisi_input.text().strip() or None,
            'is_active': self.status_checkbox.isChecked()
        }
    
    def accept(self):
        """Validate and accept"""
        tka_data = self.get_tka_data()
        validation = validate_tka_worker_data(tka_data)
        
        if not validation.is_valid:
            error_msg = "Please fix the following errors:\n\n"
            error_msg += "\n".join([error['message'] for error in validation.errors])
            QMessageBox.warning(self, "Validation Error", error_msg)
            return
        
        super().accept()

class InvoiceCreateDialog(BaseDialog):
    """Invoice creation dialog with wizard-like interface"""
    
    def __init__(self, parent=None):
        super().__init__("Create New Invoice", parent)
        self.resize(900, 700)
        self.selected_company = None
        self.invoice_lines = []
        self._setup_invoice_ui()
        self._setup_connections()
    
    def _setup_invoice_ui(self):
        """Setup invoice creation UI"""
        # Create splitter for two-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Invoice details
        left_panel = self._create_invoice_details_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Line items
        right_panel = self._create_line_items_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 500])
        
        self.add_content_widget(splitter)
        
        # Update button text
        self.set_ok_button_text("Create Invoice")
        self.enable_ok_button(False)
    
    def _create_invoice_details_panel(self) -> QWidget:
        """Create invoice details panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Panel title
        title_label = QLabel("Invoice Details")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        
        # Company selection
        self.company_search = SmartSearchWidget("Search company...")
        form_layout.addRow("Company *:", self.company_search)
        
        # Company details (read-only)
        self.company_info_label = QLabel("No company selected")
        self.company_info_label.setStyleSheet("color: #666; font-style: italic; padding: 8px; background: #f8f9fa; border-radius: 4px;")
        self.company_info_label.setWordWrap(True)
        form_layout.addRow("Company Info:", self.company_info_label)
        
        # Invoice date
        self.invoice_date = QDateEdit()
        self.invoice_date.setDate(date.today())
        self.invoice_date.setCalendarPopup(True)
        form_layout.addRow("Invoice Date:", self.invoice_date)
        
        # VAT percentage
        self.vat_percentage = NumericInputWidget()
        self.vat_percentage.setValue(11.0)
        self.vat_percentage.setSuffix("%")
        form_layout.addRow("VAT Percentage:", self.vat_percentage)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Optional notes...")
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        # Totals display
        totals_group = QGroupBox("Invoice Totals")
        totals_layout = QFormLayout(totals_group)
        
        self.subtotal_label = QLabel("Rp 0")
        self.subtotal_label.setStyleSheet("font-weight: bold;")
        totals_layout.addRow("Subtotal:", self.subtotal_label)
        
        self.vat_label = QLabel("Rp 0")
        totals_layout.addRow("VAT Amount:", self.vat_label)
        
        self.total_label = QLabel("Rp 0")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #007bff;")
        totals_layout.addRow("Total Amount:", self.total_label)
        
        layout.addWidget(totals_group)
        
        return panel
    
    def _create_line_items_panel(self) -> QWidget:
        """Create line items panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Panel title
        title_label = QLabel("Invoice Line Items")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Line items table
        self.lines_table = DataGridWidget()
        layout.addWidget(self.lines_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_line_btn = create_modern_button("Add Line Item", "success")
        self.add_line_btn.clicked.connect(self._add_line_item)
        self.add_line_btn.setEnabled(False)
        
        self.edit_line_btn = create_modern_button("Edit Selected", "primary")
        self.edit_line_btn.clicked.connect(self._edit_line_item)
        
        self.remove_line_btn = create_modern_button("Remove Selected", "danger")
        self.remove_line_btn.clicked.connect(self._remove_line_item)
        
        button_layout.addWidget(self.add_line_btn)
        button_layout.addWidget(self.edit_line_btn)
        button_layout.addWidget(self.remove_line_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return panel
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.company_search.search_triggered.connect(self._search_companies)
        self.company_search.item_selected.connect(self._select_company)
        self.vat_percentage.valueChanged.connect(self._update_totals)
    
    def _search_companies(self, query: str):
        """Search companies"""
        # This would integrate with actual search service
        # For now, mock some data
        mock_companies = [
            {'id': 1, 'company_name': 'PT Test Company 1', 'npwp': '12.345.678.9-012.345'},
            {'id': 2, 'company_name': 'PT Test Company 2', 'npwp': '98.765.432.1-098.765'}
        ]
        
        self.company_search.set_search_items(mock_companies)
    
    def _select_company(self, company_data: Dict):
        """Select company"""
        self.selected_company = company_data
        
        # Update company info display
        info_text = f"<b>{company_data['company_name']}</b><br/>"
        info_text += f"NPWP: {company_data['npwp']}"
        self.company_info_label.setText(info_text)
        
        # Enable line item addition
        self.add_line_btn.setEnabled(True)
        
        self._validate_form()
    
    def _add_line_item(self):
        """Add new line item"""
        if not self.selected_company:
            return
        
        # This would open line item dialog
        mock_line = {
            'id': len(self.invoice_lines) + 1,
            'baris': len(self.invoice_lines) + 1,
            'tka_name': 'John Doe',
            'job_name': 'Security Guard',
            'quantity': 1,
            'unit_price': 5000000,
            'line_total': 5000000
        }
        
        self.invoice_lines.append(mock_line)
        self._refresh_lines_table()
        self._update_totals()
        self._validate_form()
    
    def _edit_line_item(self):
        """Edit selected line item"""
        selected = self.lines_table.get_selected_data()
        if selected:
            QMessageBox.information(self, "Info", f"Edit line item: {selected['job_name']}")
    
    def _remove_line_item(self):
        """Remove selected line item"""
        selected = self.lines_table.get_selected_data()
        if selected:
            # Remove from list
            self.invoice_lines = [line for line in self.invoice_lines if line['id'] != selected['id']]
            self._refresh_lines_table()
            self._update_totals()
            self._validate_form()
    
    def _refresh_lines_table(self):
        """Refresh line items table"""
        columns = [
            {'key': 'baris', 'title': 'Line', 'type': 'text'},
            {'key': 'tka_name', 'title': 'TKA Worker', 'type': 'text'},
            {'key': 'job_name', 'title': 'Job Description', 'type': 'text'},
            {'key': 'quantity', 'title': 'Qty', 'type': 'text'},
            {'key': 'unit_price', 'title': 'Unit Price', 'type': 'currency'},
            {'key': 'line_total', 'title': 'Line Total', 'type': 'currency'}
        ]
        
        self.lines_table.set_data(self.invoice_lines, columns)
    
    def _update_totals(self):
        """Update invoice totals"""
        subtotal = sum(line['line_total'] for line in self.invoice_lines)
        vat_rate = self.vat_percentage.value() / 100
        vat_amount = subtotal * vat_rate
        total_amount = subtotal + vat_amount
        
        self.subtotal_label.setText(format_currency_idr(subtotal))
        self.vat_label.setText(format_currency_idr(vat_amount))
        self.total_label.setText(format_currency_idr(total_amount))
    
    def _validate_form(self):
        """Validate invoice form"""
        is_valid = (
            self.selected_company is not None and
            len(self.invoice_lines) > 0
        )
        self.enable_ok_button(is_valid)
    
    def get_invoice_data(self) -> Dict[str, Any]:
        """Get invoice data"""
        return {
            'company_id': self.selected_company['id'] if self.selected_company else None,
            'invoice_date': self.invoice_date.date().toPython(),
            'vat_percentage': Decimal(str(self.vat_percentage.value())),
            'notes': self.notes_input.toPlainText().strip(),
            'line_items': self.invoice_lines
        }

# Utility functions for dialog management
def show_login_dialog(parent=None) -> Optional[Dict[str, Any]]:
    """Show login dialog and return credentials"""
    dialog = LoginDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_credentials()
    return None

def show_company_dialog(company: Company = None, parent=None) -> Optional[Dict[str, Any]]:
    """Show company dialog and return data"""
    dialog = CompanyDialog(company, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_company_data()
    return None

def show_tka_worker_dialog(tka_worker: TkaWorker = None, parent=None) -> Optional[Dict[str, Any]]:
    """Show TKA worker dialog and return data"""
    dialog = TkaWorkerDialog(tka_worker, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_tka_data()
    return None

def show_invoice_create_dialog(parent=None) -> Optional[Dict[str, Any]]:
    """Show invoice creation dialog and return data"""
    dialog = InvoiceCreateDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_invoice_data()
    return None

def show_confirmation_dialog(title: str, message: str, parent=None) -> bool:
    """Show confirmation dialog"""
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes

def show_error_dialog(title: str, message: str, parent=None):
    """Show error dialog"""
    QMessageBox.critical(parent, title, message)

def show_info_dialog(title: str, message: str, parent=None):
    """Show information dialog"""
    QMessageBox.information(parent, title, message)

def show_warning_dialog(title: str, message: str, parent=None):
    """Show warning dialog"""
    QMessageBox.warning(parent, title, message)

if __name__ == "__main__":
    # Test dialogs
    import sys
    
    app = QApplication(sys.argv)
    
    # Test login dialog
    # credentials = show_login_dialog()
    # print(f"Login result: {credentials}")
    
    # Test company dialog
    company_data = show_company_dialog()
    print(f"Company data: {company_data}")
    
    sys.exit(0)