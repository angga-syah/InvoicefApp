# InvoiceApp
# Invoice Management System

**Professional Invoice Management System for TKA Services**

*Spirit of Services*

## 🚀 Overview

The Invoice Management System is a comprehensive, modern desktop application designed specifically for managing invoices related to TKA (Tenaga Kerja Asing/Foreign Worker) services. Built with Python and PyQt6, it provides a professional, user-friendly interface for creating, managing, and tracking invoices with advanced features including PDF generation, Excel export/import, and sophisticated business logic.

## ✨ Features

### 🏢 **Core Business Management**
- **Company Management**: Complete NPWP and IDTKU validation
- **TKA Worker Management**: Passport tracking with family member support
- **Job Description Library**: Company-specific pricing and job templates
- **Invoice Creation**: Wizard-like interface with real-time calculations

### 📄 **Advanced Invoice Features**
- **Smart Invoice Numbering**: Auto-generation with format INV-YY-MM-NNN
- **Special VAT Calculations**: Business rule .49→.48, .50→.51 rounding
- **Multi-line Items**: Support for grouped job descriptions
- **Status Workflow**: Draft → Finalized → Paid tracking
- **Professional PDF Generation**: Multi-page support with company branding

### 📊 **Reporting & Export**
- **PDF Invoice Generation**: Professional layouts with signature areas
- **Excel Export**: Multi-sheet reports with charts and analysis
- **Excel/CSV Import**: Bulk data import with validation
- **Dashboard Analytics**: Real-time statistics and recent activities

### 🎨 **Modern User Interface**
- **Responsive Design**: High-DPI support with modern styling
- **Smart Search**: Fuzzy matching with auto-completion
- **Custom Widgets**: Currency inputs, data grids, status indicators
- **Theme Support**: Light and dark themes available

### ⚡ **Performance & Reliability**
- **Intelligent Caching**: Memory and Redis-based caching
- **Database Connection Pooling**: PostgreSQL optimization
- **Background Processing**: Non-blocking UI operations
- **Comprehensive Logging**: Error tracking and performance monitoring

## 🔧 Technology Stack

- **Frontend**: PyQt6, Custom UI Components
- **Backend**: Python 3.8+, SQLAlchemy ORM
- **Database**: PostgreSQL 12+
- **PDF Generation**: ReportLab
- **Excel Processing**: OpenPyXL
- **Caching**: Redis (optional)
- **Configuration**: Pydantic Settings

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **RAM**: Minimum 4GB, Recommended 8GB
- **Storage**: 500MB free space
- **Database**: PostgreSQL 12+ server

### Required Software
1. **Python 3.8+** with pip
2. **PostgreSQL** database server
3. **Git** (for development)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/invoice-management-system.git
cd invoice-management-system
```

### 2. Setup Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env  # or your preferred editor
```

### 5. Setup Database
```bash
# Create PostgreSQL database
createdb invoice_management

# Initialize schema
python -c "from models.database import init_database; init_database()"
```

### 6. Run Application
```bash
python main.py
```

**Default Login:**
- Username: `admin`
- Password: `admin123`

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=invoice_management
DB_USER=postgres
DB_PASSWORD=your_password_here

# Application Settings
APP_NAME=Invoice Management System
DEBUG_MODE=False
SECRET_KEY=change-this-secret-key

# Business Configuration
DEFAULT_VAT_PERCENTAGE=11.00
COMPANY_TAGLINE=Spirit of Services
INVOICE_NUMBER_FORMAT=INV-{YY}-{MM}-{NNN}

# UI Configuration
DEFAULT_THEME=light
HIGH_DPI_SCALING=True
DEFAULT_FONT=Segoe UI

# Office Information
OFFICE_ADDRESS_LINE1=Jakarta Office
OFFICE_ADDRESS_LINE2=Indonesia
OFFICE_PHONE=+62-21-XXXXXXX
```

### Database Setup

#### PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql
brew services start postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

#### Database Configuration
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE invoice_management;
CREATE USER invoice_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE invoice_management TO invoice_user;
\q
```

## 🗂️ Project Structure

```
InvoiceApp/
├── 📄 main.py                      # Application entry point
├── 📄 requirements.txt             # Python dependencies
├── 📄 config.py                    # Configuration management
├── 📄 database.sql                 # Database schema
├── 📄 .env                         # Environment variables
├── 📂 models/                      # Data models and business logic
│   ├── 📄 database.py              # SQLAlchemy models
│   └── 📄 business.py              # Business logic layer
├── 📂 services/                    # Business services
│   ├── 📄 invoice_service.py       # Core invoice operations
│   ├── 📄 export_service.py        # PDF/Excel export
│   ├── 📄 import_service.py        # Excel/CSV import
│   └── 📄 cache_service.py         # Caching optimization
├── 📂 ui/                          # User interface
│   ├── 📄 main_window.py           # Main application window
│   ├── 📄 widgets.py               # Custom UI components
│   ├── 📄 dialogs.py               # Dialog windows
│   └── 📄 styles.qss               # UI styling
├── 📂 utils/                       # Utility functions
│   ├── 📄 helpers.py               # Common utilities
│   ├── 📄 validators.py            # Data validation
│   └── 📄 formatters.py            # Data formatting
├── 📂 reports/                     # Report generation
│   ├── 📄 pdf_generator.py         # PDF generation
│   └── 📄 excel_exporter.py        # Excel reports
├── 📂 assets/                      # Static resources
│   ├── 📂 icons/                   # Application icons
│   └── 📂 templates/               # Report templates
└── 📂 logs/                        # Application logs
```

## 💼 Business Logic

### Invoice Number Generation
- **Format**: `INV-YY-MM-NNN` (e.g., INV-24-12-001)
- **Auto-increment**: Per month basis
- **Collision prevention**: Database constraints

### VAT Calculation Rules
Special rounding rules for Indonesian tax compliance:
- **Rule .49**: `18,000.49 → 18,000` (round down)
- **Rule .50**: `18,000.50 → 18,001` (round up)
- **Standard**: Normal mathematical rounding for other cases

### Invoice Workflow
1. **Draft**: Fully editable, can be deleted
2. **Finalized**: Fully editable, can be deleted, ready for printing
3. **Paid**: Read-only, archived status

### Data Validation
- **NPWP**: 15-digit format validation
- **Passport**: Alphanumeric, 6-20 characters
- **Unique Constraints**: NPWP, IDTKU, Passport numbers
- **Business Rules**: TKA-Company assignments, pricing validation

## 📖 User Guide

### Getting Started

#### 1. First Login
- Use default credentials: `admin` / `admin123`
- Change password in Settings after first login

#### 2. Setup Companies
1. Navigate to **Companies** section
2. Click **Add Company**
3. Fill required information:
   - Company Name
   - NPWP (15 digits)
   - IDTKU (unique identifier)
   - Complete address

#### 3. Add TKA Workers
1. Go to **TKA Workers** section
2. Click **Add Worker**
3. Enter worker details:
   - Full name
   - Passport number (unique)
   - Gender
   - Division/Department

#### 4. Create Job Descriptions
1. Select a company
2. Add job descriptions with pricing
3. Jobs are company-specific

#### 5. Create Invoice
1. Click **Create Invoice** or use **Ctrl+N**
2. **Step 1**: Select company (with smart search)
3. **Step 2**: Add line items:
   - Select TKA worker
   - Choose job description
   - Adjust quantity/pricing if needed
4. **Step 3**: Review totals and finalize

### Advanced Features

#### Search Functionality
- **Smart Search**: Fuzzy matching with typo tolerance
- **Multi-field**: Search across names, passport, company
- **Auto-complete**: Real-time suggestions
- **Recent Items**: Quick access to recently used records

#### Batch Operations
- **Excel Import**: Use provided templates
- **Bulk Export**: Multiple invoices to single Excel file
- **Data Validation**: Pre-import error checking

#### Report Generation
- **Invoice PDFs**: Professional layout with signature areas
- **Excel Reports**: Multi-sheet analysis with charts
- **Custom Filters**: Date ranges, companies, status
- **Scheduled Reports**: Automated generation (coming soon)

## 🔍 API Reference

### Core Services

#### InvoiceService
```python
from services.invoice_service import InvoiceService

# Create invoice
with InvoiceService() as service:
    invoice, validation = service.create_invoice(
        invoice_data, line_items, user_id
    )

# Get invoice statistics
stats = service.get_invoice_statistics()
```

#### ExportService
```python
from services.export_service import export_service

# Export to PDF
pdf_path = export_service.export_invoice_pdf(invoice_id)

# Export to Excel
excel_path = export_service.export_invoices_excel([invoice_id1, invoice_id2])
```

#### ImportService
```python
from services.import_service import import_service

# Import from Excel
result = import_service.import_file(
    'companies.xlsx', 'companies', user_id
)
```

### Database Models

#### Invoice Model
```python
from models.database import Invoice, InvoiceLine

# Create invoice
invoice = Invoice(
    company_id=1,
    invoice_date=date.today(),
    vat_percentage=Decimal('11.0')
)

# Add line items
line = InvoiceLine(
    invoice_id=invoice.id,
    tka_id=1,
    job_description_id=1,
    quantity=1,
    unit_price=Decimal('5000000')
)
```

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-qt coverage

# Run all tests
pytest

# Run with coverage
coverage run -m pytest
coverage report
coverage html  # Generate HTML report
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service layer testing
- **UI Tests**: PyQt widget testing
- **Database Tests**: Model and query testing

### Test Structure
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/
│   ├── test_invoice_workflow.py
│   └── test_export_import.py
└── ui/
    ├── test_widgets.py
    └── test_dialogs.py
```

## 🚀 Deployment

### Production Setup

#### 1. Environment Configuration
```bash
# Production environment
DEBUG_MODE=False
SECRET_KEY=secure-production-key
LOG_LEVEL=WARNING

# Database optimization
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

#### 2. Database Optimization
```sql
-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_invoices_date_company 
ON invoices(invoice_date DESC, company_id);

-- Update statistics
ANALYZE;
```

#### 3. Security Considerations
- Change default passwords
- Use strong secret keys
- Enable SSL for database connections
- Regular backups
- User access controls

### Packaging

#### Windows Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed main.py
```

#### Linux Package
```bash
# Create package
python setup.py sdist bdist_wheel

# Install package
pip install dist/invoice-management-system-*.whl
```

## 🔧 Maintenance

### Backup Strategy
```bash
# Database backup
pg_dump invoice_management > backup_$(date +%Y%m%d).sql

# Application data backup
tar -czf app_backup_$(date +%Y%m%d).tar.gz exports/ logs/ assets/
```

### Performance Monitoring
- Monitor database connection pool usage
- Track cache hit rates
- Review application logs regularly
- Monitor disk space for exports/logs

### Updates
```bash
# Backup before update
./backup.sh

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run database migrations (if any)
python migrate.py

# Restart application
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Test connection
psql -h localhost -U invoice_user -d invoice_management
```

#### Permission Errors
```bash
# Fix file permissions
chmod +x main.py
chown -R $USER:$USER InvoiceApp/
```

#### Import/Export Failures
- Check file permissions in exports/ directory
- Verify Excel file format compatibility
- Check available disk space

#### UI Issues
- Verify PyQt6 installation: `python -c "import PyQt6"`
- Check display scaling settings
- Update graphics drivers

### Log Analysis
```bash
# View recent errors
tail -f logs/app.log | grep ERROR

# Search for specific issues
grep "database" logs/app.log
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/invoice-management-system.git

# Install development dependencies
pip install -r requirements.txt
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Coding Standards
- **Python**: PEP 8 compliance, type hints
- **Commits**: Conventional commit messages
- **Testing**: Minimum 80% code coverage
- **Documentation**: Docstrings for all public functions

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with tests
4. Run test suite: `pytest`
5. Update documentation
6. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PyQt6** - Modern GUI framework
- **SQLAlchemy** - Python SQL toolkit
- **ReportLab** - PDF generation library
- **OpenPyXL** - Excel file manipulation
- **PostgreSQL** - Advanced open source database

## 📞 Support

### Documentation
- **API Documentation**: [docs/api.md](docs/api.md)
- **User Manual**: [docs/user-guide.md](docs/user-guide.md)
- **Developer Guide**: [docs/developer-guide.md](docs/developer-guide.md)

### Community
- **Issues**: [GitHub Issues](https://github.com/your-org/invoice-management-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/invoice-management-system/discussions)
- **Wiki**: [Project Wiki](https://github.com/your-org/invoice-management-system/wiki)

### Contact
- **Email**: support@invoice-system.com
- **Website**: https://invoice-management-system.com

---

**Made with ❤️ for efficient TKA service management**

*Spirit of Services - Professional Invoice Management System*
