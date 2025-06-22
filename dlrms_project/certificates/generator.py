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
import base64

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
    
    def generate_certificate(self, certificate, signature_data=None, signer_name=None, sign_date=None):
        """Generate PDF certificate with optional embedded signature"""
        buffer = BytesIO()
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Add watermark
        self._add_watermark(c)
        
        # Add border
        self._add_border(c)
        
        # Add header
        self._add_header(c, certificate)
        
        # Add QR code (smaller and repositioned)
        qr_image_path = self._generate_qr_code(certificate)
        c.drawImage(qr_image_path, self.page_width - 2*inch, self.page_height - 2*inch, 
                    width=1*inch, height=1*inch)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            os.unlink(qr_image_path)
        
        # Add certificate content
        if certificate.certificate_type == 'property_contract':
            self._add_property_contract_content(c, certificate)
        else:
            self._add_parcel_certificate_content(c, certificate)
        
        # Add signatures section
        self._add_signatures_section(c, certificate, signature_data, signer_name, sign_date)
        
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
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        logo_width = 1.2 * inch
        logo_height = 1.2 * inch
        x = (self.page_width - logo_width) / 2
        y = self.page_height - 1.8 * inch

        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

        # Set text color to blue for all following text
        canvas.setFillColor(colors.HexColor('#000080'))

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
        qr = qrcode.QRCode(version=1, box_size=8, border=3)
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
        
        # Location details
        y_position -= 0.8*inch
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
        
        # Owner information - moved up to create space for signature section
        y_position -= 0.8*inch  # Reduced space before owner info
        self._add_section_header(canvas, "OWNER INFORMATION", y_position)
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Owner Name:", certificate.owner.get_full_name(), 
                       1*inch, y_position)
        # Get national ID from the owner's User model
        national_id = certificate.owner.national_id if certificate.owner.national_id else "Not provided"
        self._add_field(canvas, "National ID:", national_id, 
                       1*inch, y_position - 0.3*inch)
        if hasattr(app, 'submitted_at'):
            self._add_field(canvas, "Registration Date:", 
                           app.submitted_at.strftime("%B %d, %Y"), 
                           1*inch, y_position - 0.6*inch)
    
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
        
        # Owner information - moved up to create space for signature section
        y_position -= 0.8*inch  # Reduced space before owner info
        self._add_section_header(canvas, "OWNER INFORMATION", y_position)
        
        y_position -= 0.4*inch
        self._add_field(canvas, "Owner Name:", certificate.owner.get_full_name(), 
                       1*inch, y_position)
        # Get national ID from the owner's User model
        national_id = certificate.owner.national_id if certificate.owner.national_id else "Not provided"
        self._add_field(canvas, "National ID:", national_id, 
                       1*inch, y_position - 0.3*inch)
    
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
    
    def _add_signatures_section(self, canvas, certificate, signature_data=None, signer_name=None, sign_date=None):
        """Add signatures section with proper layout"""
        # Position signature section below owner information with proper spacing
        y_position = 3.0*inch  # Adjusted to appear below owner info
        
        # AUTHORIZED SIGNATURE text
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(self.page_width/2, y_position, "AUTHORIZED SIGNATURE")
        
        # Signature area
        y_position -= 0.5*inch
        
        # If we have signature data, embed it
        if signature_data and signature_data.startswith('data:image'):
            try:
                # Extract base64 image data
                header, data = signature_data.split(',', 1)
                image_data = base64.b64decode(data)
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    tmp_file.write(image_data)
                    tmp_file_path = tmp_file.name
                
                # Center the signature
                sig_x = (self.page_width - 2*inch) / 2
                
                # Draw the signature image
                canvas.drawImage(tmp_file_path, sig_x, y_position - 0.5*inch, 
                               width=2*inch, height=0.8*inch, preserveAspectRatio=True)
                
                # Clean up
                os.unlink(tmp_file_path)
                
                # Add signer details below signature
                y_position -= 1.0*inch
                canvas.setFont("Helvetica", 9)
                canvas.drawCentredString(self.page_width/2, y_position, "Web Master")
                y_position -= 0.2*inch
                canvas.drawCentredString(self.page_width/2, y_position, "Land Registry Officer")
                y_position -= 0.2*inch
                if sign_date:
                    canvas.drawCentredString(self.page_width/2, y_position, 
                                           f"Date: {sign_date.strftime('%B %d, %Y')}")
            except Exception as e:
                print(f"Error embedding signature: {e}")
                # Fall back to empty signature box
                self._draw_signature_box(canvas, y_position)
        else:
            # Draw empty signature box centered
            self._draw_signature_box(canvas, y_position)
            
            # Add signer details below
            y_position -= 1.0*inch
            canvas.setFont("Helvetica", 9)
            canvas.drawCentredString(self.page_width/2, y_position, "Web Master")
            y_position -= 0.2*inch
            canvas.drawCentredString(self.page_width/2, y_position, "Land Registry Officer")
            y_position -= 0.2*inch
            canvas.drawCentredString(self.page_width/2, y_position, "Date: ___________")
    
    def _draw_signature_box(self, canvas, y_position):
        """Draw a signature box with label"""
        # Draw the signature line
        canvas.setLineWidth(0.5)
        sig_x = (self.page_width - 2*inch) / 2
        canvas.line(sig_x, y_position, sig_x + 2*inch, y_position)
    
    def _add_footer(self, canvas, certificate):
        """Add footer with verification info"""
        # Use smaller font for footer
        canvas.setFont("Helvetica", 7)
        
        # Position footer content carefully
        y_position = 1.2*inch
        
        # Verification URL - break it if too long
        url = certificate.verification_url
        if len(url) > 70:
            canvas.drawCentredString(self.page_width/2, y_position, 
                                    f" ")
            canvas.drawCentredString(self.page_width/2, y_position - 0.15*inch, 
                                    f" ")
            y_position -= 0.3*inch
        else:
            canvas.drawCentredString(self.page_width/2, y_position, 
                                    f"Verification URL: {url}")
            y_position -= 0.2*inch
        
        # Official document text
        canvas.drawCentredString(self.page_width/2, y_position, 
                                "This is an official document of the Government of the Democratic Republic of the Congo")
        y_position -= 0.15*inch
        
        canvas.drawCentredString(self.page_width/2, y_position, 
                                "Document officiel du Gouvernement de la République Démocratique du Congo")