"""
Invoice Management System - Main Application Window
The main application window with navigation, content areas, and comprehensive
UI management for the invoice management system.
"""

import os
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QToolBar, QStatusBar, QMenuBar, QMenu,
    QMessageBox, QFileDialog, QProgressBar, QFrame, QGroupBox,
    QTabWidget, QScrollArea, QApplication, QHeaderView,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize
from PyQt6.QtGui import QAction, QIcon, QFont, QPixmap, QKeySequence

from models.database import get_db_session, init_database
from services.invoice_service import InvoiceService, create_invoice_service
from services.export_service import export_service
from services.import_service import import_service
from services.cache_service import warm_up_cache, cleanup_cache
from ui.widgets import (
    SmartSearchWidget, DataGridWidget, StatusIndicator, ModernButton,
    LoadingSpinner, AnimatedCard, create_modern_button, create_data_grid,
    create_search_widget
)
from ui.dialogs import (
    show_login_dialog, show_company_dialog, show_tka_worker_dialog,
    show_invoice_create_dialog, show_confirmation_dialog, show_error_dialog,
    show_info_dialog, show_warning_dialog
)
from utils.formatters import format_currency_idr, format_date_short
from config import app_config, ui_config

logger = logging.getLogger(__name__)

class DashboardWidget(QWidget):
    """Dashboard widget with overview cards and statistics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_timer()
    
    def _setup_ui(self):
        """Setup dashboard UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Welcome section
        welcome_frame = QFrame()
        welcome_frame.setProperty("cardWidget", True)
        welcome_layout = QVBoxLayout(welcome_frame)
        
        welcome_title = QLabel(f"Welcome to {app_config.name}")
        welcome_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        
        welcome_subtitle = QLabel("Manage your invoices with ease and efficiency")
        welcome_subtitle.setStyleSheet("color: #666; margin-bottom: 10px;")
        
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_subtitle)
        
        layout.addWidget(welcome_frame)
        
        # Statistics cards
        stats_layout = QGridLayout()
        
        # Create statistics cards
        self.total_invoices_card = self._create_stat_card("Total Invoices", "0", "#007bff")
        self.pending_invoices_card = self._create_stat_card("Pending", "0", "#ffc107")
        self.paid_invoices_card = self._create_stat_card("Paid", "0", "#28a745")
        self.total_amount_card = self._create_stat_card("Total Amount", "Rp 0", "#17a2b8")
        
        stats_layout.addWidget(self.total_invoices_card, 0, 0)
        stats_layout.addWidget(self.pending_invoices_card, 0, 1)
        stats_layout.addWidget(self.paid_invoices_card, 0, 2)
        stats_layout.addWidget(self.total_amount_card, 0, 3)
        
        layout.addLayout(stats_layout)
        
        # Recent activities
        recent_frame = QFrame()
        recent_frame.setProperty("cardWidget", True)
        recent_layout = QVBoxLayout(recent_frame)
        
        recent_title = QLabel("Recent Activities")
        recent_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        recent_layout.addWidget(recent_title)
        
        self.recent_activities = QLabel("Loading recent activities...")
        self.recent_activities.setStyleSheet("color: #666;")
        recent_layout.addWidget(self.recent_activities)
        
        layout.addWidget(recent_frame)
        
        layout.addStretch()
    
    def _create_stat_card(self, title: str, value: str, color: str) -> AnimatedCard:
        """Create statistics card"""
        card = AnimatedCard()
        card.setFixedHeight(100)
        
        card_layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 5px;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        value_label.setObjectName("value_label")  # For easy access
        
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()
        
        # Replace card's layout
        card.setLayout(card_layout)
        
        return card
    
    def _setup_timer(self):
        """Setup refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Initial load
        QTimer.singleShot(1000, self.refresh_data)
    
    def refresh_data(self):
        """Refresh dashboard data"""
        try:
            with create_invoice_service() as service:
                stats = service.get_invoice_statistics()
                
                # Update statistics cards
                self._update_stat_card(self.total_invoices_card, str(stats.get('total_invoices', 0)))
                self._update_stat_card(self.pending_invoices_card, str(stats.get('status_counts', {}).get('draft', 0)))
                self._update_stat_card(self.paid_invoices_card, str(stats.get('status_counts', {}).get('paid', 0)))
                
                total_amount = sum(stats.get('status_amounts', {}).values())
                self._update_stat_card(self.total_amount_card, format_currency_idr(total_amount))
                
                # Update recent activities
                recent_count = stats.get('recent_count', 0)
                self.recent_activities.setText(f"{recent_count} new invoices created today")
                
        except Exception as e:
            logger.error(f"Error refreshing dashboard data: {e}")
    
    def _update_stat_card(self, card: AnimatedCard, value: str):
        """Update statistics card value"""
        value_label = card.findChild(QLabel, "value_label")
        if value_label:
            value_label.setText(value)

class InvoicesWidget(QWidget):
    """Invoices management widget"""
    
    invoice_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup invoices UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header with actions
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Invoice Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Action buttons
        self.create_btn = create_modern_button("Create Invoice", "success")
        self.edit_btn = create_modern_button("Edit", "primary")
        self.delete_btn = create_modern_button("Delete", "danger")
        self.export_btn = create_modern_button("Export", "info")
        
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        header_layout.addWidget(self.create_btn)
        header_layout.addWidget(self.edit_btn)
        header_layout.addWidget(self.delete_btn)
        header_layout.addWidget(self.export_btn)
        
        layout.addLayout(header_layout)
        
        # Search and filters
        filter_layout = QHBoxLayout()
        
        self.search_widget = create_search_widget("Search invoices...")
        filter_layout.addWidget(self.search_widget)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Draft", "Finalized", "Paid", "Cancelled"])
        filter_layout.addWidget(self.status_filter)
        
        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All Time", "Today", "This Week", "This Month", "Last Month"])
        filter_layout.addWidget(self.date_filter)
        
        layout.addLayout(filter_layout)
        
        # Invoices table
        self.invoices_table = create_data_grid()
        layout.addWidget(self.invoices_table)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.loading_spinner = LoadingSpinner(16)
        self.loading_spinner.hide()
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.loading_spinner)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.create_btn.clicked.connect(self._create_invoice)
        self.edit_btn.clicked.connect(self._edit_invoice)
        self.delete_btn.clicked.connect(self._delete_invoice)
        self.export_btn.clicked.connect(self._export_invoices)
        
        self.search_widget.search_triggered.connect(self._search_invoices)
        self.search_widget.search_cleared.connect(self._clear_search)
        
        self.status_filter.currentTextChanged.connect(self._filter_changed)
        self.date_filter.currentTextChanged.connect(self._filter_changed)
        
        self.invoices_table.row_selected.connect(self._invoice_selected)
        self.invoices_table.row_double_clicked.connect(self._invoice_double_clicked)
        
        # Load initial data
        QTimer.singleShot(500, self.refresh_invoices)
    
    def _create_invoice(self):
        """Create new invoice"""
        invoice_data = show_invoice_create_dialog(self)
        if invoice_data:
            # This would create the actual invoice
            show_info_dialog("Success", "Invoice created successfully!", self)
            self.refresh_invoices()
    
    def _edit_invoice(self):
        """Edit selected invoice"""
        selected = self.invoices_table.get_selected_data()
        if selected:
            show_info_dialog("Info", f"Edit invoice: {selected.get('invoice_number', 'Unknown')}", self)
    
    def _delete_invoice(self):
        """Delete selected invoice"""
        selected = self.invoices_table.get_selected_data()
        if selected:
            if show_confirmation_dialog("Confirm Delete", 
                                      f"Are you sure you want to delete invoice {selected.get('invoice_number', 'Unknown')}?", 
                                      self):
                show_info_dialog("Info", "Invoice deletion will be implemented", self)
    
    def _export_invoices(self):
        """Export invoices"""
        # Show export options dialog
        show_info_dialog("Info", "Export functionality will be implemented", self)
    
    def _search_invoices(self, query: str):
        """Search invoices"""
        self.status_label.setText(f"Searching for: {query}")
        self.refresh_invoices()
    
    def _clear_search(self):
        """Clear search"""
        self.status_label.setText("Ready")
        self.refresh_invoices()
    
    def _filter_changed(self):
        """Handle filter change"""
        self.refresh_invoices()
    
    def _invoice_selected(self, row: int, data: dict):
        """Handle invoice selection"""
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.invoice_selected.emit(data)
    
    def _invoice_double_clicked(self, row: int, data: dict):
        """Handle invoice double click"""
        self._edit_invoice()
    
    def refresh_invoices(self):
        """Refresh invoices list"""
        self.loading_spinner.start()
        self.status_label.setText("Loading invoices...")
        
        try:
            # Mock data for now
            mock_invoices = [
                {
                    'id': 1,
                    'invoice_number': 'INV-24-12-001',
                    'company_name': 'PT Test Company 1',
                    'invoice_date': date.today(),
                    'total_amount': 5500000,
                    'status': 'draft',
                    'created_at': datetime.now()
                },
                {
                    'id': 2,
                    'invoice_number': 'INV-24-12-002',
                    'company_name': 'PT Test Company 2',
                    'invoice_date': date.today(),
                    'total_amount': 7250000,
                    'status': 'finalized',
                    'created_at': datetime.now()
                }
            ]
            
            columns = [
                {'key': 'invoice_number', 'title': 'Invoice Number', 'type': 'text'},
                {'key': 'company_name', 'title': 'Company', 'type': 'text'},
                {'key': 'invoice_date', 'title': 'Date', 'type': 'date'},
                {'key': 'total_amount', 'title': 'Total Amount', 'type': 'currency'},
                {'key': 'status', 'title': 'Status', 'type': 'status'}
            ]
            
            self.invoices_table.set_data(mock_invoices, columns)
            
            self.status_label.setText(f"Loaded {len(mock_invoices)} invoices")
            
        except Exception as e:
            logger.error(f"Error loading invoices: {e}")
            show_error_dialog("Error", f"Failed to load invoices: {str(e)}", self)
            self.status_label.setText("Error loading invoices")
        
        finally:
            self.loading_spinner.stop()

class CompaniesWidget(QWidget):
    """Companies management widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup companies UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Company Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Action buttons
        self.create_btn = create_modern_button("Add Company", "success")
        self.edit_btn = create_modern_button("Edit", "primary")
        self.delete_btn = create_modern_button("Delete", "danger")
        
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        header_layout.addWidget(self.create_btn)
        header_layout.addWidget(self.edit_btn)
        header_layout.addWidget(self.delete_btn)
        
        layout.addLayout(header_layout)
        
        # Search
        self.search_widget = create_search_widget("Search companies...")
        layout.addWidget(self.search_widget)
        
        # Companies table
        self.companies_table = create_data_grid()
        layout.addWidget(self.companies_table)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.create_btn.clicked.connect(self._create_company)
        self.edit_btn.clicked.connect(self._edit_company)
        self.delete_btn.clicked.connect(self._delete_company)
        
        self.companies_table.row_selected.connect(self._company_selected)
        self.companies_table.row_double_clicked.connect(self._company_double_clicked)
        
        QTimer.singleShot(500, self.refresh_companies)
    
    def _create_company(self):
        """Create new company"""
        company_data = show_company_dialog(parent=self)
        if company_data:
            show_info_dialog("Success", "Company created successfully!", self)
            self.refresh_companies()
    
    def _edit_company(self):
        """Edit selected company"""
        selected = self.companies_table.get_selected_data()
        if selected:
            # Mock company object for editing
            show_info_dialog("Info", f"Edit company: {selected.get('company_name', 'Unknown')}", self)
    
    def _delete_company(self):
        """Delete selected company"""
        selected = self.companies_table.get_selected_data()
        if selected:
            if show_confirmation_dialog("Confirm Delete", 
                                      f"Are you sure you want to delete {selected.get('company_name', 'Unknown')}?", 
                                      self):
                show_info_dialog("Info", "Company deletion will be implemented", self)
    
    def _company_selected(self, row: int, data: dict):
        """Handle company selection"""
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
    
    def _company_double_clicked(self, row: int, data: dict):
        """Handle company double click"""
        self._edit_company()
    
    def refresh_companies(self):
        """Refresh companies list"""
        # Mock data
        mock_companies = [
            {
                'id': 1,
                'company_name': 'PT Test Company 1',
                'npwp': '12.345.678.9-012.345',
                'idtku': 'IDTKU001',
                'is_active': True
            },
            {
                'id': 2,
                'company_name': 'PT Test Company 2',
                'npwp': '98.765.432.1-098.765',
                'idtku': 'IDTKU002',
                'is_active': True
            }
        ]
        
        columns = [
            {'key': 'company_name', 'title': 'Company Name', 'type': 'text'},
            {'key': 'npwp', 'title': 'NPWP', 'type': 'npwp'},
            {'key': 'idtku', 'title': 'IDTKU', 'type': 'text'},
            {'key': 'is_active', 'title': 'Status', 'type': 'status'}
        ]
        
        self.companies_table.set_data(mock_companies, columns)

class TkaWorkersWidget(QWidget):
    """TKA Workers management widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup TKA workers UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("TKA Workers Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Action buttons
        self.create_btn = create_modern_button("Add Worker", "success")
        self.edit_btn = create_modern_button("Edit", "primary")
        self.delete_btn = create_modern_button("Delete", "danger")
        
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        header_layout.addWidget(self.create_btn)
        header_layout.addWidget(self.edit_btn)
        header_layout.addWidget(self.delete_btn)
        
        layout.addLayout(header_layout)
        
        # Search
        self.search_widget = create_search_widget("Search TKA workers...")
        layout.addWidget(self.search_widget)
        
        # TKA workers table
        self.workers_table = create_data_grid()
        layout.addWidget(self.workers_table)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.create_btn.clicked.connect(self._create_worker)
        self.edit_btn.clicked.connect(self._edit_worker)
        self.delete_btn.clicked.connect(self._delete_worker)
        
        self.workers_table.row_selected.connect(self._worker_selected)
        self.workers_table.row_double_clicked.connect(self._worker_double_clicked)
        
        QTimer.singleShot(500, self.refresh_workers)
    
    def _create_worker(self):
        """Create new TKA worker"""
        worker_data = show_tka_worker_dialog(parent=self)
        if worker_data:
            show_info_dialog("Success", "TKA worker created successfully!", self)
            self.refresh_workers()
    
    def _edit_worker(self):
        """Edit selected worker"""
        selected = self.workers_table.get_selected_data()
        if selected:
            show_info_dialog("Info", f"Edit worker: {selected.get('nama', 'Unknown')}", self)
    
    def _delete_worker(self):
        """Delete selected worker"""
        selected = self.workers_table.get_selected_data()
        if selected:
            if show_confirmation_dialog("Confirm Delete", 
                                      f"Are you sure you want to delete {selected.get('nama', 'Unknown')}?", 
                                      self):
                show_info_dialog("Info", "Worker deletion will be implemented", self)
    
    def _worker_selected(self, row: int, data: dict):
        """Handle worker selection"""
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
    
    def _worker_double_clicked(self, row: int, data: dict):
        """Handle worker double click"""
        self._edit_worker()
    
    def refresh_workers(self):
        """Refresh workers list"""
        # Mock data
        mock_workers = [
            {
                'id': 1,
                'nama': 'John Doe',
                'passport': 'A1234567',
                'divisi': 'Security',
                'jenis_kelamin': 'Laki-laki',
                'is_active': True
            },
            {
                'id': 2,
                'nama': 'Jane Smith',
                'passport': 'B7654321',
                'divisi': 'Cleaning',
                'jenis_kelamin': 'Perempuan',
                'is_active': True
            }
        ]
        
        columns = [
            {'key': 'nama', 'title': 'Name', 'type': 'text'},
            {'key': 'passport', 'title': 'Passport', 'type': 'text'},
            {'key': 'divisi', 'title': 'Division', 'type': 'text'},
            {'key': 'jenis_kelamin', 'title': 'Gender', 'type': 'text'},
            {'key': 'is_active', 'title': 'Status', 'type': 'status'}
        ]
        
        self.workers_table.set_data(mock_workers, columns)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.setWindowTitle(app_config.name)
        self.resize(1200, 800)
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_tool_bar()
        self._setup_status_bar()
        self._setup_connections()
        
        # Show login dialog
        self._show_login()
    
    def _setup_ui(self):
        """Setup main UI"""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Navigation panel
        self.nav_widget = self._create_navigation_panel()
        splitter.addWidget(self.nav_widget)
        
        # Content area
        self.content_stack = QStackedWidget()
        splitter.addWidget(self.content_stack)
        
        # Set splitter proportions
        splitter.setSizes([250, 950])
        
        # Create content widgets
        self._create_content_widgets()
    
    def _create_navigation_panel(self) -> QWidget:
        """Create navigation panel"""
        nav_widget = QWidget()
        nav_widget.setFixedWidth(250)
        nav_widget.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #e9ecef;")
        
        layout = QVBoxLayout(nav_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # App title
        title_label = QLabel(app_config.name)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 20px;")
        layout.addWidget(title_label)
        
        # Navigation tree
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setRootIsDecorated(False)
        self.nav_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QTreeWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        # Add navigation items
        nav_items = [
            ("🏠", "Dashboard"),
            ("📄", "Invoices"),
            ("🏢", "Companies"),
            ("👥", "TKA Workers"),
            ("📊", "Reports"),
            ("⚙️", "Settings")
        ]
        
        for icon, text in nav_items:
            item = QTreeWidgetItem([f"{icon}  {text}"])
            item.setData(0, Qt.ItemDataRole.UserRole, text.lower().replace(" ", "_"))
            self.nav_tree.addTopLevelItem(item)
        
        layout.addWidget(self.nav_tree)
        layout.addStretch()
        
        # User info
        user_frame = QFrame()
        user_frame.setProperty("cardWidget", True)
        user_layout = QVBoxLayout(user_frame)
        
        self.user_label = QLabel("Not logged in")
        self.user_label.setStyleSheet("font-weight: bold; color: #333;")
        user_layout.addWidget(self.user_label)
        
        logout_btn = create_modern_button("Logout", "outline-primary")
        logout_btn.clicked.connect(self._logout)
        user_layout.addWidget(logout_btn)
        
        layout.addWidget(user_frame)
        
        return nav_widget
    
    def _create_content_widgets(self):
        """Create content widgets"""
        # Dashboard
        self.dashboard_widget = DashboardWidget()
        self.content_stack.addWidget(self.dashboard_widget)
        
        # Invoices
        self.invoices_widget = InvoicesWidget()
        self.content_stack.addWidget(self.invoices_widget)
        
        # Companies
        self.companies_widget = CompaniesWidget()
        self.content_stack.addWidget(self.companies_widget)
        
        # TKA Workers
        self.tka_workers_widget = TkaWorkersWidget()
        self.content_stack.addWidget(self.tka_workers_widget)
        
        # Reports (placeholder)
        reports_widget = QLabel("Reports functionality will be implemented")
        reports_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reports_widget.setStyleSheet("font-size: 16px; color: #666;")
        self.content_stack.addWidget(reports_widget)
        
        # Settings (placeholder)
        settings_widget = QLabel("Settings functionality will be implemented")
        settings_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_widget.setStyleSheet("font-size: 16px; color: #666;")
        self.content_stack.addWidget(settings_widget)
        
        # Set initial widget
        self.content_stack.setCurrentWidget(self.dashboard_widget)
    
    def _setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_invoice_action = QAction("New Invoice", self)
        new_invoice_action.setShortcut(QKeySequence.StandardKey.New)
        new_invoice_action.triggered.connect(self._new_invoice)
        file_menu.addAction(new_invoice_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Import Data", self)
        import_action.triggered.connect(self._import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export Data", self)
        export_action.triggered.connect(self._export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self._refresh_current_view)
        view_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_tool_bar(self):
        """Setup tool bar"""
        toolbar = self.addToolBar("Main")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # New invoice
        new_invoice_action = QAction("📄 New Invoice", self)
        new_invoice_action.triggered.connect(self._new_invoice)
        toolbar.addAction(new_invoice_action)
        
        toolbar.addSeparator()
        
        # Refresh
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self._refresh_current_view)
        toolbar.addAction(refresh_action)
        
        # Export
        export_action = QAction("📤 Export", self)
        export_action.triggered.connect(self._export_data)
        toolbar.addAction(export_action)
    
    def _setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Add permanent widgets
        self.connection_label = QLabel("🔗 Connected")
        self.connection_label.setStyleSheet("color: #28a745;")
        self.status_bar.addPermanentWidget(self.connection_label)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.nav_tree.itemClicked.connect(self._nav_item_clicked)
    
    def _show_login(self):
        """Show login dialog"""
        credentials = show_login_dialog(self)
        if credentials:
            # Mock login validation
            if credentials['username'] == 'admin' and credentials['password'] == 'admin123':
                self.current_user = {
                    'username': credentials['username'],
                    'full_name': 'System Administrator',
                    'role': 'admin'
                }
                self.user_label.setText(f"Welcome, {self.current_user['full_name']}")
                self.status_bar.showMessage("Login successful")
                
                # Warm up cache
                warm_up_cache()
            else:
                show_error_dialog("Login Failed", "Invalid username or password", self)
                self.close()
        else:
            self.close()
    
    def _logout(self):
        """Logout user"""
        if show_confirmation_dialog("Confirm Logout", "Are you sure you want to logout?", self):
            self.current_user = None
            cleanup_cache()
            self.close()
    
    def _nav_item_clicked(self, item: QTreeWidgetItem):
        """Handle navigation item click"""
        page_name = item.data(0, Qt.ItemDataRole.UserRole)
        
        widget_map = {
            'dashboard': 0,
            'invoices': 1,
            'companies': 2,
            'tka_workers': 3,
            'reports': 4,
            'settings': 5
        }
        
        if page_name in widget_map:
            self.content_stack.setCurrentIndex(widget_map[page_name])
            self.status_bar.showMessage(f"Switched to {item.text(0)}")
    
    def _new_invoice(self):
        """Create new invoice"""
        self.content_stack.setCurrentWidget(self.invoices_widget)
        self.invoices_widget._create_invoice()
    
    def _import_data(self):
        """Import data from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "", 
            "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            show_info_dialog("Info", f"Import from {file_path} will be implemented", self)
    
    def _export_data(self):
        """Export data to file"""
        show_info_dialog("Info", "Export functionality will be implemented", self)
    
    def _refresh_current_view(self):
        """Refresh current view"""
        current_widget = self.content_stack.currentWidget()
        
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()
        elif hasattr(current_widget, 'refresh_invoices'):
            current_widget.refresh_invoices()
        elif hasattr(current_widget, 'refresh_companies'):
            current_widget.refresh_companies()
        elif hasattr(current_widget, 'refresh_workers'):
            current_widget.refresh_workers()
        
        self.status_bar.showMessage("View refreshed")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h3>{app_config.name}</h3>
        <p>Version {app_config.version}</p>
        <p>Professional invoice management system for TKA services.</p>
        <p><b>{app_config.company_tagline}</b></p>
        <p>Built with PyQt6 and modern design principles.</p>
        """
        QMessageBox.about(self, "About", about_text)
    
    def closeEvent(self, event):
        """Handle close event"""
        cleanup_cache()
        event.accept()

if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    app.setApplicationName(app_config.name)
    app.setApplicationVersion(app_config.version)
    
    # Load styles
    try:
        with open("ui/styles.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        logger.warning("Styles file not found, using default styling")
    
    # Initialize database
    try:
        init_database()
    except Exception as e:
        QMessageBox.critical(None, "Database Error", f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())