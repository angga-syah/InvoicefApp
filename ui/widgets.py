"""
Invoice Management System - Custom UI Widgets
Advanced custom widgets for modern user interface including smart search,
currency inputs, data grids, and interactive components.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable, Union
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLineEdit, QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTextEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy, QCompleter,
    QStyledItemDelegate, QApplication, QToolButton, QCheckBox, QGroupBox,
    QScrollArea, QProgressBar, QSlider, QTabWidget, QSplitter
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QAbstractTableModel, QModelIndex,
    QVariant, QSize, QPropertyAnimation, QEasingCurve, QRect, QEvent
)
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPalette, QColor, QIcon, QPainter, QPen, QBrush,
    QPixmap, QValidator, QIntValidator, QDoubleValidator, QRegularExpressionValidator
)

from utils.formatters import (
    format_currency_idr, format_currency_input, parse_currency_input,
    format_date_short, format_npwp_display
)
from utils.validators import ValidationResult
from utils.helpers import safe_decimal, fuzzy_search_score

logger = logging.getLogger(__name__)

class SearchCompleter(QCompleter):
    """Custom completer with fuzzy search support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_items = []
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
    
    def set_search_items(self, items: List[Dict[str, Any]]):
        """Set items for search completion"""
        self.search_items = items
        
        # Create string list for completer
        completion_strings = []
        for item in items:
            # Add searchable fields
            if 'name' in item:
                completion_strings.append(item['name'])
            if 'nama' in item:
                completion_strings.append(item['nama'])
            if 'company_name' in item:
                completion_strings.append(item['company_name'])
            if 'invoice_number' in item:
                completion_strings.append(item['invoice_number'])
        
        from PyQt6.QtCore import QStringListModel
        model = QStringListModel(completion_strings)
        self.setModel(model)

class SmartSearchWidget(QWidget):
    """Advanced search widget with fuzzy matching and auto-completion"""
    
    # Signals
    search_triggered = pyqtSignal(str)  # Emitted when search should be performed
    item_selected = pyqtSignal(dict)    # Emitted when item is selected
    search_cleared = pyqtSignal()       # Emitted when search is cleared
    
    def __init__(self, placeholder_text="Search...", parent=None):
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self.search_items = []
        self.filtered_items = []
        self.debounce_timer = QTimer()
        self.debounce_timer.timeout.connect(self._perform_search)
        self.debounce_timer.setSingleShot(True)
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.placeholder_text)
        self.search_input.setProperty("searchWidget", True)
        
        # Search icon button
        self.search_button = QToolButton()
        self.search_button.setText("🔍")
        self.search_button.setToolTip("Search")
        
        # Clear button
        self.clear_button = QToolButton()
        self.clear_button.setText("✕")
        self.clear_button.setToolTip("Clear search")
        self.clear_button.setVisible(False)
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.search_button)
        layout.addWidget(self.clear_button)
        
        # Setup completer
        self.completer = SearchCompleter(self)
        self.search_input.setCompleter(self.completer)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_button.clicked.connect(self._trigger_search)
        self.clear_button.clicked.connect(self.clear_search)
        self.search_input.returnPressed.connect(self._trigger_search)
    
    def _on_text_changed(self, text: str):
        """Handle text change with debouncing"""
        self.clear_button.setVisible(bool(text))
        
        # Restart debounce timer
        self.debounce_timer.stop()
        self.debounce_timer.start(300)  # 300ms debounce
    
    def _perform_search(self):
        """Perform actual search"""
        query = self.search_input.text().strip()
        if query:
            self.search_triggered.emit(query)
        else:
            self.search_cleared.emit()
    
    def _trigger_search(self):
        """Trigger immediate search"""
        self.debounce_timer.stop()
        self._perform_search()
    
    def clear_search(self):
        """Clear search input"""
        self.search_input.clear()
        self.search_cleared.emit()
    
    def set_search_items(self, items: List[Dict[str, Any]]):
        """Set items available for search"""
        self.search_items = items
        self.completer.set_search_items(items)
    
    def get_query(self) -> str:
        """Get current search query"""
        return self.search_input.text().strip()

class CurrencyInputWidget(QWidget):
    """Currency input widget with formatting and validation"""
    
    # Signals
    value_changed = pyqtSignal(Decimal)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_value = Decimal('0')
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Currency label
        self.currency_label = QLabel("Rp")
        self.currency_label.setStyleSheet("font-weight: bold; color: #666;")
        
        # Amount input
        self.amount_input = QLineEdit()
        self.amount_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.amount_input.setPlaceholderText("0")
        
        # Validation
        self.validator = QRegularExpressionValidator()
        self.validator.setRegularExpression(r'^[\d,.]*$')
        self.amount_input.setValidator(self.validator)
        
        layout.addWidget(self.currency_label)
        layout.addWidget(self.amount_input)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.amount_input.textChanged.connect(self._on_text_changed)
        self.amount_input.editingFinished.connect(self._format_display)
    
    def _on_text_changed(self, text: str):
        """Handle text change"""
        # Parse and validate input
        try:
            value = parse_currency_input(text)
            if value != self.current_value:
                self.current_value = value
                self.value_changed.emit(value)
        except Exception:
            pass
    
    def _format_display(self):
        """Format display value"""
        if self.current_value:
            formatted = format_currency_input(str(int(self.current_value)))
            self.amount_input.setText(formatted)
    
    def get_value(self) -> Decimal:
        """Get current decimal value"""
        return self.current_value
    
    def set_value(self, value: Union[Decimal, float, int, str]):
        """Set value"""
        try:
            decimal_value = safe_decimal(value)
            self.current_value = decimal_value
            formatted = format_currency_input(str(int(decimal_value)))
            self.amount_input.setText(formatted)
            self.value_changed.emit(decimal_value)
        except Exception as e:
            logger.error(f"Error setting currency value: {e}")
    
    def clear(self):
        """Clear input"""
        self.amount_input.clear()
        self.current_value = Decimal('0')

class AutoCompleteComboBox(QComboBox):
    """ComboBox with auto-completion support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # Setup completer
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self.completer)
    
    def set_items(self, items: List[str]):
        """Set items with auto-completion"""
        self.clear()
        self.addItems(items)
        
        # Update completer
        from PyQt6.QtCore import QStringListModel
        model = QStringListModel(items)
        self.completer.setModel(model)

class NumericInputWidget(QDoubleSpinBox):
    """Enhanced numeric input with better formatting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(2)
        self.setRange(0, 999999999.99)
        self.setGroupSeparatorShown(True)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.PlusMinus)
    
    def textFromValue(self, value: float) -> str:
        """Custom text formatting"""
        if value == 0:
            return "0"
        return f"{value:,.2f}".rstrip('0').rstrip('.')

class StatusIndicator(QLabel):
    """Visual status indicator widget"""
    
    def __init__(self, status: str = "active", parent=None):
        super().__init__(parent)
        self.current_status = status
        self._update_appearance()
    
    def set_status(self, status: str):
        """Set status and update appearance"""
        self.current_status = status
        self._update_appearance()
    
    def _update_appearance(self):
        """Update visual appearance based on status"""
        status_config = {
            'active': {'text': 'Active', 'color': '#28a745'},
            'inactive': {'text': 'Inactive', 'color': '#dc3545'},
            'draft': {'text': 'Draft', 'color': '#ffc107'},
            'finalized': {'text': 'Finalized', 'color': '#28a745'},
            'paid': {'text': 'Paid', 'color': '#17a2b8'},
            'cancelled': {'text': 'Cancelled', 'color': '#dc3545'}
        }
        
        config = status_config.get(self.current_status, {'text': self.current_status, 'color': '#6c757d'})
        
        self.setText(config['text'])
        self.setProperty("status", self.current_status)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {config['color']}20;
                color: {config['color']};
                border: 1px solid {config['color']}40;
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: 500;
            }}
        """)

class DataGridWidget(QTableWidget):
    """Enhanced table widget with advanced features"""
    
    # Signals
    row_selected = pyqtSignal(int, dict)
    row_double_clicked = pyqtSignal(int, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_data = []
        self._setup_table()
        self._setup_connections()
    
    def _setup_table(self):
        """Setup table properties"""
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        
        # Header properties
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Vertical header
        self.verticalHeader().setVisible(False)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_double_click)
    
    def set_data(self, data: List[Dict[str, Any]], columns: List[Dict[str, str]]):
        """
        Set table data
        
        Args:
            data: List of row data dictionaries
            columns: List of column definitions with 'key', 'title', 'type' keys
        """
        self.row_data = data
        
        # Setup columns
        self.setColumnCount(len(columns))
        headers = [col['title'] for col in columns]
        self.setHorizontalHeaderLabels(headers)
        
        # Setup rows
        self.setRowCount(len(data))
        
        # Populate data
        for row_idx, row_data in enumerate(data):
            for col_idx, col_config in enumerate(columns):
                value = row_data.get(col_config['key'], '')
                
                # Format value based on type
                formatted_value = self._format_cell_value(value, col_config.get('type', 'text'))
                
                item = QTableWidgetItem(str(formatted_value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                
                # Store original value
                item.setData(Qt.ItemDataRole.UserRole, value)
                
                self.setItem(row_idx, col_idx, item)
        
        # Auto-resize columns
        self.resizeColumnsToContents()
    
    def _format_cell_value(self, value: Any, cell_type: str) -> str:
        """Format cell value based on type"""
        if value is None or value == '':
            return ''
        
        if cell_type == 'currency':
            return format_currency_idr(value, show_symbol=False)
        elif cell_type == 'date':
            if isinstance(value, (date, datetime)):
                return format_date_short(value)
            return str(value)
        elif cell_type == 'status':
            return str(value).title()
        elif cell_type == 'npwp':
            return format_npwp_display(str(value))
        else:
            return str(value)
    
    def _on_selection_changed(self):
        """Handle selection change"""
        current_row = self.currentRow()
        if 0 <= current_row < len(self.row_data):
            self.row_selected.emit(current_row, self.row_data[current_row])
    
    def _on_double_click(self, item):
        """Handle double click"""
        row = item.row()
        if 0 <= row < len(self.row_data):
            self.row_double_clicked.emit(row, self.row_data[row])
    
    def get_selected_data(self) -> Optional[Dict[str, Any]]:
        """Get currently selected row data"""
        current_row = self.currentRow()
        if 0 <= current_row < len(self.row_data):
            return self.row_data[current_row]
        return None
    
    def filter_data(self, filter_func: Callable[[Dict], bool]):
        """Filter table data"""
        filtered_data = [row for row in self.row_data if filter_func(row)]
        
        # Hide/show rows based on filter
        for row in range(self.rowCount()):
            should_show = row < len(filtered_data)
            self.setRowHidden(row, not should_show)

class AnimatedCard(QFrame):
    """Animated card widget with hover effects"""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str = "", content: str = "", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.content_text = content
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self):
        """Setup card UI"""
        self.setProperty("cardWidget", True)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        self.title_label = QLabel(self.title_text)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        
        # Content
        self.content_label = QLabel(self.content_text)
        self.content_label.setStyleSheet("color: #666; font-size: 12px;")
        self.content_label.setWordWrap(True)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.content_label)
        layout.addStretch()
    
    def _setup_animation(self):
        """Setup hover animation"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def set_title(self, title: str):
        """Set card title"""
        self.title_text = title
        self.title_label.setText(title)
    
    def set_content(self, content: str):
        """Set card content"""
        self.content_text = content
        self.content_label.setText(content)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        # Subtle scale effect would go here
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        # Reset scale effect would go here
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ModernButton(QPushButton):
    """Modern styled button with variants"""
    
    def __init__(self, text: str = "", button_style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.button_style = button_style
        self.setProperty("buttonStyle", button_style)
        self._setup_style()
    
    def _setup_style(self):
        """Setup button style"""
        self.setMinimumHeight(36)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def set_style(self, style: str):
        """Change button style"""
        self.button_style = style
        self.setProperty("buttonStyle", style)
        self.style().unpolish(self)
        self.style().polish(self)

class LoadingSpinner(QWidget):
    """Loading spinner widget"""
    
    def __init__(self, size: int = 32, parent=None):
        super().__init__(parent)
        self.size = size
        self.angle = 0
        self.setFixedSize(size, size)
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._rotate)
        self.timer.setInterval(50)  # 20 FPS
    
    def start(self):
        """Start spinning"""
        self.timer.start()
        self.show()
    
    def stop(self):
        """Stop spinning"""
        self.timer.stop()
        self.hide()
    
    def _rotate(self):
        """Rotate spinner"""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """Paint spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw spinner
        rect = self.rect()
        painter.translate(rect.center())
        painter.rotate(self.angle)
        
        pen = QPen(QColor("#007bff"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Draw arcs
        for i in range(8):
            alpha = 255 - (i * 30)
            color = QColor("#007bff")
            color.setAlpha(max(alpha, 50))
            pen.setColor(color)
            painter.setPen(pen)
            
            painter.drawLine(0, -self.size//3, 0, -self.size//2 + 2)
            painter.rotate(45)

class IconButton(QToolButton):
    """Icon button with tooltip"""
    
    def __init__(self, icon_text: str = "⚙", tooltip: str = "", parent=None):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setFixedSize(32, 32)
        self.setStyleSheet("""
            QToolButton {
                border: 1px solid transparent;
                border-radius: 16px;
                background-color: transparent;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: #e3f2fd;
                border-color: #bbdefb;
            }
            QToolButton:pressed {
                background-color: #bbdefb;
            }
        """)

# Factory functions for common widgets
def create_search_widget(placeholder: str = "Search...") -> SmartSearchWidget:
    """Create configured search widget"""
    return SmartSearchWidget(placeholder)

def create_currency_input() -> CurrencyInputWidget:
    """Create configured currency input"""
    return CurrencyInputWidget()

def create_data_grid() -> DataGridWidget:
    """Create configured data grid"""
    return DataGridWidget()

def create_status_indicator(status: str) -> StatusIndicator:
    """Create status indicator"""
    return StatusIndicator(status)

def create_modern_button(text: str, style: str = "primary") -> ModernButton:
    """Create modern button"""
    return ModernButton(text, style)

if __name__ == "__main__":
    # Test widgets
    import sys
    
    app = QApplication(sys.argv)
    
    # Test window
    window = QWidget()
    window.setWindowTitle("Widget Tests")
    window.resize(800, 600)
    
    layout = QVBoxLayout(window)
    
    # Test search widget
    search = create_search_widget("Search companies...")
    layout.addWidget(search)
    
    # Test currency input
    currency = create_currency_input()
    currency.set_value(1234567.89)
    layout.addWidget(currency)
    
    # Test buttons
    btn_layout = QHBoxLayout()
    for style in ["primary", "secondary", "success", "danger"]:
        btn = create_modern_button(style.title(), style)
        btn_layout.addWidget(btn)
    layout.addLayout(btn_layout)
    
    # Test status indicators
    status_layout = QHBoxLayout()
    for status in ["active", "draft", "finalized", "paid"]:
        indicator = create_status_indicator(status)
        status_layout.addWidget(indicator)
    layout.addLayout(status_layout)
    
    # Test data grid
    grid = create_data_grid()
    test_data = [
        {'id': 1, 'name': 'Test Company 1', 'amount': 1500000, 'status': 'active'},
        {'id': 2, 'name': 'Test Company 2', 'amount': 2750000, 'status': 'inactive'}
    ]
    columns = [
        {'key': 'name', 'title': 'Company Name', 'type': 'text'},
        {'key': 'amount', 'title': 'Amount', 'type': 'currency'},
        {'key': 'status', 'title': 'Status', 'type': 'status'}
    ]
    grid.set_data(test_data, columns)
    layout.addWidget(grid)
    
    window.show()
    
    print("✅ Custom widgets test window created")
    sys.exit(app.exec())