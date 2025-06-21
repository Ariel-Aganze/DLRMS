from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
from io import BytesIO
from datetime import datetime
import hashlib
from django.conf import settings
from django.core.files.base import ContentFile
import os
from PIL import Image
import tempfile

class CertificateGenerator:
    """Generate PDF certificates for land parcels"""
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CertificateTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#000080'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='Header',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#000080'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Legal text style
        self.styles.add(ParagraphStyle(
            name='LegalText',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        ))
    
    def generate_certificate(self, certificate):
        """Generate PDF certificate"""
        buffer = BytesIO()
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Add watermark
        self._add_watermark(c)
        
        # Add border
        self._add_border(c)
        
        # Add header
        self._add_header(c, certificate)
        
        # Add QR code
        qr_image_path = self._generate_qr_code(certificate)
        c.drawImage(qr_image_path, self.page_width - 2.5*inch, self.page_height - 2.5*inch, 
                    width=1.5*inch, height=1.5*inch)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            os.unlink(qr_image_path)
        
        # Add certificate content
        if certificate.certificate_type == 'property_contract':
            self._add_property_contract_content(c, certificate)
        else:
            self._add_parcel_certificate_content(c, certificate)
        
        # Add signatures section
        self._add_signatures_section(c, certificate)
        
        # Add footer
        self._add_footer(c, certificate)
        
        # Save PDF
        c.save()
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Calculate document hash
        document_hash = hashlib.sha256(pdf_content).hexdigest()
        
        return pdf_content, document_hash
    
    def _add_watermark(self, canvas):
        """Add watermark to the page"""
        canvas.saveState()
        canvas.setFillColor(colors.lightgrey, alpha=0.1)
        canvas.setFont("Helvetica-Bold", 60)
        canvas.translate(self.page_width/2, self.page_height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "DRC LAND REGISTRY")
        canvas.restoreState()
    
    def _add_border(self, canvas):
        """Add decorative border"""
        canvas.setStrokeColor(colors.HexColor('#000080'))
        canvas.setLineWidth(2)
        # Outer border
        canvas.rect(0.5*inch, 0.5*inch, 
                   self.page_width - inch, 
                   self.page_height - inch)
        # Inner border
        canvas.setLineWidth(0.5)
        canvas.rect(0.6*inch, 0.6*inch, 
                   self.page_width - 1.2*inch, 
                   self.page_height - 1.2*inch)
    
    def _add_header(self, canvas, certificate):
        """Add certificate header"""
        # Government emblem placeholder
        # Government logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')  # Update path as needed
        logo_width = 1.2 * inch
        logo_height = 1.2 * inch
        x = (self.page_width - logo_width) / 2
        y = self.page_height - 1.8 * inch

        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')  # ✅ Fix black background

    # Set text color to blue for all following text
        canvas.setFillColor(colors.HexColor('#000080'))  # ✅ Apply blue color before drawing text

    # Country name
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(self.page_width/2, self.page_height - 2.5*inch, 
                            "DEMOCRATIC REPUBLIC OF THE CONGO")

    # Ministry
        canvas.setFont("Helvetica", 14)
        canvas.drawCentredString(self.page_width/2, self.page_height - 2.8*inch, 
                            "MINISTRY OF LAND AFFAIRS")

    # System name
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(self.page_width/2, self.page_height - 3.1*inch, 
                            "DIGITAL LAND REGISTRY MANAGEMENT SYSTEM")

    # Certificate title
        canvas.setFont("Helvetica-Bold", 20)
        title = "PROPERTY CONTRACT CERTIFICATE" if certificate.certificate_type == 'property_contract' else "PARCEL CERTIFICATE OF OWNERSHIP"
        canvas.drawCentredString(self.page_width/2, self.page_height - 3.7*inch, title)

    
    def _generate_qr_code(self, certificate):
        """Generate QR code for certificate verification"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(certificate.verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Create a temporary file for the QR code
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file, format='PNG')
            tmp_file_path = tmp_file.name
        
        return tmp_file_path
    
    def _add_property_contract_content(self, canvas, certificate):
        """Add content specific to property contract"""
        y_position = self.page_height - 4.5*inch
        
        # Certificate details
        self._add_field(canvas, "Certificate Number:", certificate.certificate_number, 
                       1*inch, y_position)
        self._add_field(canvas, "Issue Date:", certificate.issue_date.strftime("%B %d, %Y"), 
                       1*inch, y_position - 0.3*inch)
        self._add_field(canvas, "Expiry Date:", certificate.expiry_date.strftime("%B %d, %Y"), 
                       1*inch, y_position - 0.6*inch)
        
        # Property information
        y_position -= 1.2*inch
        self._add_section_header(canvas, "PROPERTY INFORMATION", y_position)
        
        app = certificate.application
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Application Number:", app.application_number, 1*inch, y_position)
        self._add_field(canvas, "Property Address:", app.property_address, 1*inch, y_position - 0.3*inch)
        
        # Location details (using province/district terminology for DRC)
        y_position -= 0.8*inch
        # For DRC context, we might not have all admin divisions, so use what's available
        self._add_field(canvas, "Location:", app.property_address, 1*inch, y_position)
        
        # Property details
        y_position -= 0.5*inch
        self._add_field(canvas, "Property Type:", app.property_type, 
                       1*inch, y_position)
        if hasattr(app, 'size_hectares') and app.size_hectares:
            self._add_field(canvas, "Land Size:", f"{app.size_hectares} hectares", 
                           3.5*inch, y_position)
        
        if hasattr(app, 'latitude') and app.latitude and hasattr(app, 'longitude') and app.longitude:
            self._add_field(canvas, "GPS Coordinates:", 
                           f"Lat: {app.latitude}, Long: {app.longitude}", 
                           1*inch, y_position - 0.3*inch)
        
        # Owner information
        y_position -= 1*inch
        self._add_section_header(canvas, "OWNER INFORMATION", y_position)
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Owner Name:", certificate.owner.get_full_name(), 
                       1*inch, y_position)
        self._add_field(canvas, "National ID:", app.applicant.username, 
                       1*inch, y_position - 0.3*inch)
        if hasattr(app, 'submitted_at'):
            self._add_field(canvas, "Registration Date:", 
                           app.submitted_at.strftime("%B %d, %Y"), 
                           1*inch, y_position - 0.6*inch)
        
        # Legal statement
        y_position -= 1.2*inch
        self._add_legal_statement(canvas, certificate, y_position)
    
    def _add_parcel_certificate_content(self, canvas, certificate):
        """Add content specific to parcel certificate"""
        y_position = self.page_height - 4.5*inch
        
        # Certificate details
        self._add_field(canvas, "Certificate Number:", certificate.certificate_number, 
                       1*inch, y_position)
        
        # Generate title number based on certificate number
        title_number = f"TITLE-{certificate.certificate_number}"
        
        self._add_field(canvas, "Title Number:", title_number, 
                       1*inch, y_position - 0.3*inch)
        self._add_field(canvas, "Issue Date:", certificate.issue_date.strftime("%B %d, %Y"), 
                       1*inch, y_position - 0.6*inch)
        self._add_field(canvas, "Validity:", "LIFETIME", 
                       1*inch, y_position - 0.9*inch)
        
        # Property information
        y_position -= 1.5*inch
        self._add_section_header(canvas, "PROPERTY INFORMATION", y_position)
        
        app = certificate.application
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Application Number:", app.application_number, 1*inch, y_position)
        self._add_field(canvas, "Property Address:", app.property_address, 1*inch, y_position - 0.3*inch)
        
        # Property details
        y_position -= 0.8*inch
        self._add_field(canvas, "Property Type:", app.property_type, 
                       1*inch, y_position)
        if hasattr(app, 'size_hectares') and app.size_hectares:
            self._add_field(canvas, "Land Size:", f"{app.size_hectares} hectares", 
                           3.5*inch, y_position)
        
        if hasattr(app, 'latitude') and app.latitude and hasattr(app, 'longitude') and app.longitude:
            self._add_field(canvas, "GPS Coordinates:", 
                           f"Lat: {app.latitude}, Long: {app.longitude}", 
                           1*inch, y_position - 0.3*inch)
        
        # Owner information
        y_position -= 1*inch
        self._add_section_header(canvas, "OWNER INFORMATION", y_position)
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Owner Name:", certificate.owner.get_full_name(), 
                       1*inch, y_position)
        self._add_field(canvas, "National ID:", app.applicant.username, 
                       1*inch, y_position - 0.3*inch)
        
        # Legal statement for parcel certificate
        y_position -= 1.2*inch
        canvas.setFont("Helvetica", 10)
        legal_text = """This Parcel Certificate certifies permanent ownership of the above-described property. 
This certificate supersedes any previous Property Contracts and remains valid indefinitely 
unless legally transferred or revoked by competent authority.

The owner has full rights to use, transfer, mortgage, or inherit this property in 
accordance with the laws of the Democratic Republic of the Congo."""
        
        # Draw legal text with word wrap
        text_lines = legal_text.split('\n')
        for line in text_lines:
            canvas.drawString(1*inch, y_position, line)
            y_position -= 0.2*inch
    
    def _add_field(self, canvas, label, value, x, y):
        """Add a field with label and value"""
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(x, y, label)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(x + 1.5*inch, y, str(value))
    
    def _add_section_header(self, canvas, text, y):
        """Add a section header"""
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.HexColor('#000080'))
        canvas.drawString(1*inch, y, text)
        canvas.setFillColor(colors.black)
    
    def _add_legal_statement(self, canvas, certificate, y_position):
        """Add legal statement"""
        canvas.setFont("Helvetica", 10)
        
        if certificate.certificate_type == 'property_contract':
            legal_text = """This Property Contract certifies that the above-named person has rightful ownership 
of the described property for a period of three (3) years from the issue date. 
This contract must be renewed or converted to a Parcel Certificate before expiry.

Issued in accordance with the Land Law of the Democratic Republic of the Congo."""
        
        # Draw legal text with word wrap
        text_lines = legal_text.split('\n')
        for line in text_lines:
            canvas.drawString(1*inch, y_position, line)
            y_position -= 0.2*inch
    
    def _add_signatures_section(self, canvas, certificate):
        """Add signatures section"""
        y_position = 3*inch
        
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(1*inch, y_position, "AUTHORIZED SIGNATURES")
        
        # Signature boxes
        y_position -= 0.5*inch
        
        # Registry Officer
        self._draw_signature_box(canvas, "Land Registry Officer", 1*inch, y_position)
        
        # Property Owner
        self._draw_signature_box(canvas, "Property Owner", 3*inch, y_position)
        
        # Witness
        self._draw_signature_box(canvas, "Witness", 5*inch, y_position)
    
    def _draw_signature_box(self, canvas, title, x, y):
        """Draw a signature box"""
        canvas.setLineWidth(0.5)
        canvas.line(x, y, x + 1.5*inch, y)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(x + 0.75*inch, y - 0.2*inch, title)
        canvas.drawCentredString(x + 0.75*inch, y - 0.35*inch, "Date: ___________")
    
    def _add_footer(self, canvas, certificate):
        """Add footer with verification info"""
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(self.page_width/2, 1*inch, 
                                f"Verification URL: {certificate.verification_url}")
        canvas.drawCentredString(self.page_width/2, 0.8*inch, 
                                "This is an official document of the Government of the Democratic Republic of the Congo")
        canvas.drawCentredString(self.page_width/2, 0.6*inch, 
                                "Document officiel du Gouvernement de la République Démocratique du Congo")