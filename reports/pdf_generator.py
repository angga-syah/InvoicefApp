"""
Invoice Management System - PDF Report Generator
Advanced PDF generation for invoices with professional layouts,
multi-page support, and customizable templates.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Frame, PageTemplate, BaseDocTemplate, NextPageTemplate
)
from reportlab.platypus.flowables import Flowable, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics import renderPDF

from models.database import Invoice, InvoiceLine
from services.invoice_service import InvoiceService
from utils.formatters import (
    format_currency_idr, format_date_long, format_date_short,
    format_currency_words, format_npwp_display
)
from utils.helpers import ensure_directory, safe_filename
from config import app_config, export_config

logger = logging.getLogger(__name__)

class InvoicePageTemplate(PageTemplate):
    """Custom page template for invoices"""
    
    def __init__(self, id, frames, **kwargs):
        super().__init__(id, frames, **kwargs)
        self.invoice_data = kwargs.get('invoice_data', {})
    
    def beforeDrawPage(self, canvas, doc):
        """Called before each page is drawn"""
        # Page header
        self._draw_header(canvas, doc)
        
        # Page footer (only on last page)
        if hasattr(doc, '_current_page') and doc._current_page == doc._total_pages:
            self._draw_footer(canvas, doc)
    
    def _draw_header(self, canvas, doc):
        """Draw page header"""
        width, height = letter
        
        # Company name
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawCentredText(width / 2, height - 50, app_config.name)
        
        # Tagline
        canvas.setFont("Helvetica-Oblique", 12)
        canvas.drawCentredText(width / 2, height - 70, app_config.company_tagline)
        
        # Office info
        canvas.setFont("Helvetica", 10)
        canvas.drawCentredText(width / 2, height - 90, app_config.office_address_line1)
        canvas.drawCentredText(width / 2, height - 105, app_config.office_address_line2)
        canvas.drawCentredText(width / 2, height - 120, f"Telp: {app_config.office_phone}")
        
        # Invoice details (top right)
        if self.invoice_data:
            invoice_date = self.invoice_data.get('invoice_date', date.today())
            invoice_number = self.invoice_data.get('invoice_number', '')
            
            canvas.setFont("Helvetica", 10)
            canvas.drawRightString(width - 72, height - 50, f"Jakarta, {format_date_long(invoice_date)}")
            canvas.drawRightString(width - 72, height - 65, f"No. Invoice: {invoice_number}")
            
            # Page number
            if hasattr(doc, '_current_page') and hasattr(doc, '_total_pages'):
                canvas.drawRightString(width - 72, height - 80, f"Halaman: {doc._current_page} dari {doc._total_pages}")
    
    def _draw_footer(self, canvas, doc):
        """Draw page footer (only on last page)"""
        # This will be called by the flowable that determines it's the last page
        pass

class SignatureSection(Flowable):
    """Signature section flowable"""
    
    def __init__(self, invoice_data: Dict, width: float = 6*inch):
        self.invoice_data = invoice_data
        self.width = width
        self.height = 3*inch
    
    def draw(self):
        """Draw signature section"""
        canvas = self.canv
        
        # Bank information (if available)
        bank_account = self.invoice_data.get('bank_account')
        if bank_account:
            y_pos = self.height - 20
            
            canvas.setFont("Helvetica-Bold", 10)
            canvas.drawString(0, y_pos, "Transfer ke:")
            
            canvas.setFont("Helvetica", 10)
            y_pos -= 15
            canvas.drawString(0, y_pos, f"Bank: {bank_account.get('bank_name', '')}")
            
            y_pos -= 15
            canvas.drawString(0, y_pos, f"No. Rekening: {bank_account.get('account_number', '')}")
            
            y_pos -= 15
            canvas.drawString(0, y_pos, f"Atas Nama: {bank_account.get('account_name', '')}")
        
        # Signature area
        signature_x = self.width - 2*inch
        signature_y = self.height - 40
        
        canvas.setFont("Helvetica", 10)
        canvas.drawCentredText(signature_x, signature_y, "Hormat kami,")
        
        # Space for signature
        signature_y -= 60
        
        # Name
        creator_name = self.invoice_data.get('creator_name', '')
        canvas.drawCentredText(signature_x, signature_y, f"({creator_name})")

class PDFGenerator:
    """Main PDF generator class"""
    
    def __init__(self):
        self.page_size = letter
        self.margin = 0.75 * inch
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Invoice title style
        self.styles.add(ParagraphStyle(
            'InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Recipient info style
        self.styles.add(ParagraphStyle(
            'RecipientInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
            leftIndent=0
        ))
        
        # Table cell styles
        self.styles.add(ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT,
            leading=10
        ))
        
        self.styles.add(ParagraphStyle(
            'TableCellCenter',
            parent=self.styles['TableCell'],
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            'TableCellRight',
            parent=self.styles['TableCell'],
            alignment=TA_RIGHT
        ))
    
    def generate_invoice_pdf(self, invoice_id: int, output_path: str = None, 
                           template_options: Dict = None) -> str:
        """
        Generate PDF for invoice with advanced layout
        
        Args:
            invoice_id: ID of invoice to generate
            output_path: Optional custom output path
            template_options: Optional template customization options
            
        Returns:
            Path to generated PDF file
        """
        with InvoiceService() as service:
            invoice = service.get_invoice(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            # Generate filename if not provided
            if not output_path:
                filename = safe_filename(f"Invoice_{invoice.invoice_number}.pdf")
                output_dir = ensure_directory(export_config.export_directory)
                output_path = output_dir / filename
            
            # Prepare invoice data for template
            invoice_data = self._prepare_invoice_data(invoice)
            
            # Calculate total pages (needed for header)
            total_pages = self._calculate_total_pages(invoice)
            
            # Create PDF document with custom template
            doc = self._create_document(str(output_path), invoice_data, total_pages)
            
            # Build PDF content
            story = self._build_invoice_story(invoice, invoice_data, template_options or {})
            
            # Generate PDF
            doc.build(story)
            
            logger.info(f"Generated PDF for invoice {invoice.invoice_number}: {output_path}")
            return str(output_path)
    
    def _prepare_invoice_data(self, invoice: Invoice) -> Dict[str, Any]:
        """Prepare invoice data for template"""
        bank_account = None
        if invoice.bank_account:
            bank_account = {
                'bank_name': invoice.bank_account.bank_name,
                'account_number': invoice.bank_account.account_number,
                'account_name': invoice.bank_account.account_name
            }
        
        return {
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date,
            'company_name': invoice.company.company_name,
            'company_npwp': invoice.company.npwp,
            'company_address': invoice.company.address,
            'subtotal': invoice.subtotal,
            'vat_percentage': invoice.vat_percentage,
            'vat_amount': invoice.vat_amount,
            'total_amount': invoice.total_amount,
            'creator_name': invoice.creator.full_name,
            'bank_account': bank_account,
            'notes': invoice.notes
        }
    
    def _calculate_total_pages(self, invoice: Invoice) -> int:
        """Calculate total pages needed for invoice"""
        # Simple calculation based on number of lines
        # This is a rough estimate - actual pagination may vary
        lines_count = len(invoice.lines)
        lines_per_page = 20  # Estimated lines per page
        
        base_pages = 1
        if lines_count > lines_per_page:
            base_pages = (lines_count // lines_per_page) + (1 if lines_count % lines_per_page else 0)
        
        return base_pages
    
    def _create_document(self, output_path: str, invoice_data: Dict, total_pages: int) -> BaseDocTemplate:
        """Create PDF document with custom page template"""
        doc = BaseDocTemplate(
            output_path,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=1.5*inch,  # More space for header
            bottomMargin=self.margin
        )
        
        # Store page info for template
        doc._total_pages = total_pages
        doc._current_page = 1
        
        # Create frame for content
        frame = Frame(
            self.margin, self.margin,
            self.page_size[0] - 2*self.margin,
            self.page_size[1] - 2.5*inch,  # Account for header space
            id='normal'
        )
        
        # Create page template
        template = InvoicePageTemplate(
            'invoice',
            [frame],
            invoice_data=invoice_data
        )
        
        doc.addPageTemplates([template])
        
        return doc
    
    def _build_invoice_story(self, invoice: Invoice, invoice_data: Dict, 
                           template_options: Dict) -> List:
        """Build complete invoice story"""
        story = []
        
        # Invoice title
        story.append(Paragraph("INVOICE", self.styles['InvoiceTitle']))
        story.append(Spacer(1, 12))
        
        # Recipient information
        story.extend(self._build_recipient_section(invoice_data))
        
        # Invoice items table
        story.extend(self._build_invoice_table(invoice))
        
        # Totals section
        story.extend(self._build_totals_section(invoice_data))
        
        # Amount in words
        story.extend(self._build_amount_words_section(invoice_data))
        
        # Signature section (will appear on last page)
        story.append(SignatureSection(invoice_data))
        
        return story
    
    def _build_recipient_section(self, invoice_data: Dict) -> List:
        """Build recipient information section"""
        content = []
        
        # "Kepada:" label
        content.append(Paragraph("Kepada:", self.styles['RecipientInfo']))
        
        # Company information
        company_info = f"<b>{invoice_data['company_name']}</b><br/>"
        company_info += f"NPWP: {format_npwp_display(invoice_data['company_npwp'])}<br/>"
        company_info += invoice_data['company_address']
        
        content.append(Paragraph(company_info, self.styles['RecipientInfo']))
        content.append(Spacer(1, 20))
        
        return content
    
    def _build_invoice_table(self, invoice: Invoice) -> List:
        """Build invoice items table with professional styling"""
        content = []
        
        # Table headers
        headers = [
            Paragraph('<b>No</b>', self.styles['TableCellCenter']),
            Paragraph('<b>Tanggal</b>', self.styles['TableCellCenter']),
            Paragraph('<b>Expatriat</b>', self.styles['TableCellCenter']),
            Paragraph('<b>Keterangan</b>', self.styles['TableCellCenter']),
            Paragraph('<b>Harga (Rp)</b>', self.styles['TableCellCenter'])
        ]
        
        # Table data
        table_data = [headers]
        
        for line in invoice.lines:
            # TKA name
            tka_name = line.tka_worker.nama if line.tka_worker else "Unknown"
            
            # Job description
            job_name = line.custom_job_name or (
                line.job_description.job_name if line.job_description else ""
            )
            job_desc = line.custom_job_description or (
                line.job_description.job_description if line.job_description else ""
            )
            
            # Format description
            keterangan = job_name
            if line.quantity > 1:
                keterangan += f" ({line.quantity}x)"
            if job_desc and job_desc != job_name:
                keterangan += f"<br/><i>{job_desc}</i>"
            
            row = [
                Paragraph(str(line.baris), self.styles['TableCellCenter']),
                Paragraph(format_date_short(invoice.invoice_date), self.styles['TableCellCenter']),
                Paragraph(tka_name, self.styles['TableCell']),
                Paragraph(keterangan, self.styles['TableCell']),
                Paragraph(format_currency_idr(line.line_total, show_symbol=False), self.styles['TableCellRight'])
            ]
            table_data.append(row)
        
        # Create table
        col_widths = [0.6*inch, 1*inch, 1.5*inch, 2.3*inch, 1.1*inch]
        invoice_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Enhanced table styling
        table_style = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)])
        ]
        
        invoice_table.setStyle(TableStyle(table_style))
        
        # Wrap table in KeepTogether to avoid orphan headers
        content.append(KeepTogether(invoice_table))
        content.append(Spacer(1, 20))
        
        return content
    
    def _build_totals_section(self, invoice_data: Dict) -> List:
        """Build totals section"""
        content = []
        
        # Totals table (right-aligned)
        totals_data = [
            ['', 'Subtotal:', format_currency_idr(invoice_data['subtotal'], show_symbol=False)],
            ['', f"PPN {invoice_data['vat_percentage']}%:", format_currency_idr(invoice_data['vat_amount'], show_symbol=False)],
            ['', 'Total:', format_currency_idr(invoice_data['total_amount'], show_symbol=False)]
        ]
        
        totals_table = Table(totals_data, colWidths=[3.5*inch, 1.2*inch, 1.3*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, -1), (-1, -1), 12),
            ('LINEABOVE', (1, -1), (-1, -1), 1.5, colors.black),
            ('TOPPADDING', (1, -1), (-1, -1), 8),
        ]))
        
        content.append(totals_table)
        content.append(Spacer(1, 15))
        
        return content
    
    def _build_amount_words_section(self, invoice_data: Dict) -> List:
        """Build amount in words section"""
        content = []
        
        amount_words = format_currency_words(invoice_data['total_amount'])
        words_para = Paragraph(
            f"<b>Terbilang:</b> <i>{amount_words}</i>", 
            self.styles['RecipientInfo']
        )
        content.append(words_para)
        content.append(Spacer(1, 25))
        
        return content

class BatchPDFGenerator:
    """Generator for batch PDF operations"""
    
    def __init__(self):
        self.pdf_generator = PDFGenerator()
    
    def generate_multiple_invoices(self, invoice_ids: List[int], 
                                 output_directory: str = None) -> List[str]:
        """Generate PDFs for multiple invoices"""
        if not output_directory:
            output_directory = ensure_directory(export_config.export_directory)
        
        generated_files = []
        
        for invoice_id in invoice_ids:
            try:
                output_path = self.pdf_generator.generate_invoice_pdf(
                    invoice_id, 
                    str(Path(output_directory) / f"Invoice_{invoice_id}.pdf")
                )
                generated_files.append(output_path)
            except Exception as e:
                logger.error(f"Failed to generate PDF for invoice {invoice_id}: {e}")
        
        return generated_files
    
    def generate_invoices_by_criteria(self, criteria: Dict[str, Any], 
                                    output_directory: str = None) -> List[str]:
        """Generate PDFs for invoices matching criteria"""
        with InvoiceService() as service:
            result = service.get_invoices_list(
                page=1, 
                per_page=1000,  # Large number to get all matching
                filters=criteria
            )
            
            invoice_ids = [inv['id'] for inv in result['invoices']]
            return self.generate_multiple_invoices(invoice_ids, output_directory)

# Global instances
pdf_generator = PDFGenerator()
batch_pdf_generator = BatchPDFGenerator()

def generate_invoice_pdf(invoice_id: int, output_path: str = None) -> str:
    """Convenience function to generate invoice PDF"""
    return pdf_generator.generate_invoice_pdf(invoice_id, output_path)

def generate_multiple_invoice_pdfs(invoice_ids: List[int], output_directory: str = None) -> List[str]:
    """Convenience function to generate multiple invoice PDFs"""
    return batch_pdf_generator.generate_multiple_invoices(invoice_ids, output_directory)

if __name__ == "__main__":
    # Test PDF generator
    print("Testing PDF generator...")
    
    try:
        # Test would require actual invoice data
        # pdf_path = generate_invoice_pdf(1)
        # print(f"Generated PDF: {pdf_path}")
        
        print("✅ PDF generator initialized successfully")
        
    except Exception as e:
        print(f"❌ PDF generator test failed: {e}")