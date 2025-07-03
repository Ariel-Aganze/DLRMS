# Add this class to certificates/certificate_generator.py or create a new file

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import qrcode
from io import BytesIO
from datetime import datetime
import hashlib
from django.conf import settings
from django.core.files.base import ContentFile
import os
import tempfile

class TransferCertificateGenerator:
    """Generate professional PDF certificates for land ownership transfers"""
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='TransferTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#000080'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='TransferHeader',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#000080'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#000080'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
    
    def generate_transfer_certificate(self, transfer, notary):
        """Generate professional PDF transfer certificate"""
        buffer = BytesIO()
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Add watermark
        self._add_watermark(c)
        
        # Add border
        self._add_border(c)
        
        # Add header with logo
        self._add_header(c, transfer)
        
        # Add QR code for verification
        qr_image_path = self._generate_qr_code(transfer)
        c.drawImage(qr_image_path, self.page_width - 2*inch, self.page_height - 2*inch, 
                    width=1*inch, height=1*inch)
        
        # Clean up temporary file
        if os.path.exists(qr_image_path):
            os.unlink(qr_image_path)
        
        # Add certificate content
        self._add_transfer_content(c, transfer)
        
        # Add declaration
        self._add_declaration(c, transfer)
        
        # Add signatures section
        self._add_signatures_section(c, transfer, notary)
        
        # Add footer
        self._add_footer(c, transfer)
        
        # Add page number
        c.setFont("Helvetica", 8)
        c.drawRightString(self.page_width - 0.5*inch, 0.5*inch, "Page 1 of 1")
        
        # Save PDF
        c.save()
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def _add_watermark(self, canvas):
        """Add watermark to the page"""
        canvas.saveState()
        canvas.setFillColor(colors.lightgrey, alpha=0.1)
        canvas.setFont("Helvetica-Bold", 50)
        canvas.translate(self.page_width/2, self.page_height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "OFFICIAL TRANSFER")
        canvas.restoreState()
    
    def _add_border(self, canvas):
        """Add decorative double border"""
        canvas.setStrokeColor(colors.HexColor('#000080'))
        # Outer border
        canvas.setLineWidth(2)
        canvas.rect(0.4*inch, 0.4*inch, 
                   self.page_width - 0.8*inch, 
                   self.page_height - 0.8*inch)
        # Inner border
        canvas.setLineWidth(0.5)
        canvas.rect(0.5*inch, 0.5*inch, 
                   self.page_width - 1.0*inch, 
                   self.page_height - 1.0*inch)
    
    def _add_header(self, canvas, transfer):
        """Add certificate header with official styling"""
        # Government logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, (self.page_width - 1.2*inch)/2, 
                           self.page_height - 1.8*inch, 
                           width=1.2*inch, height=1.2*inch, 
                           preserveAspectRatio=True, mask='auto')
        
        # Country name
        canvas.setFillColor(colors.HexColor('#000080'))
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(self.page_width/2, self.page_height - 2.2*inch, 
                               "DEMOCRATIC REPUBLIC OF THE CONGO")
        
        # Ministry
        canvas.setFont("Helvetica", 14)
        canvas.drawCentredString(self.page_width/2, self.page_height - 2.5*inch, 
                               "MINISTRY OF LAND AFFAIRS")
        
        # System name
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(self.page_width/2, self.page_height - 2.8*inch, 
                               "DIGITAL LAND REGISTRY MANAGEMENT SYSTEM")
        
        # Certificate title
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawCentredString(self.page_width/2, self.page_height - 3.4*inch, 
                               "CERTIFICATE OF LAND OWNERSHIP TRANSFER")
        
        # Certificate number
        canvas.setFont("Helvetica-Bold", 14)
        canvas.setFillColor(colors.black)
        canvas.drawCentredString(self.page_width/2, self.page_height - 3.8*inch, 
                               f"Certificate No: {transfer.transfer_number}")
    
    def _generate_qr_code(self, transfer):
        """Generate QR code for certificate verification"""
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        verification_url = f"https://dlrms.gov.cd/verify/transfer/{transfer.transfer_number}"
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file, format='PNG')
            return tmp_file.name
    
    def _add_transfer_content(self, canvas, transfer):
        """Add main transfer content"""
        y_position = self.page_height - 4.5*inch
        
        # Transfer Details Section
        self._add_section_header(canvas, "TRANSFER DETAILS", y_position)
        y_position -= 0.3*inch
        
        self._add_field(canvas, "Transfer Date:", 
                       transfer.completed_at.strftime("%B %d, %Y"), 
                       1*inch, y_position)
        y_position -= 0.25*inch
        
        reason_display = transfer.get_reason_display()
        if transfer.reason == 'other' and transfer.other_reason:
            reason_display += f" ({transfer.other_reason})"
        self._add_field(canvas, "Transfer Reason:", reason_display, 1*inch, y_position)
        
        if transfer.transfer_value:
            y_position -= 0.25*inch
            self._add_field(canvas, "Transfer Value:", 
                           f"${transfer.transfer_value:,.2f}", 
                           1*inch, y_position)
        
        # Parties Section
        y_position -= 0.6*inch
        self._add_section_header(canvas, "PARTIES INVOLVED", y_position)
        y_position -= 0.3*inch
        
        # Previous Owner
        self._add_field(canvas, "Previous Owner:", 
                       transfer.current_owner.get_full_name(), 
                       1*inch, y_position)
        y_position -= 0.25*inch
        self._add_field(canvas, "National ID:", 
                       transfer.current_owner.national_id, 
                       1.5*inch, y_position)
        
        # New Owner
        y_position -= 0.35*inch
        self._add_field(canvas, "New Owner:", 
                       transfer.new_owner.get_full_name(), 
                       1*inch, y_position)
        y_position -= 0.25*inch
        self._add_field(canvas, "National ID:", 
                       transfer.new_owner.national_id, 
                       1.5*inch, y_position)
        
        # Property Information Section
        y_position -= 0.6*inch
        self._add_section_header(canvas, "PROPERTY INFORMATION", y_position)
        y_position -= 0.3*inch
        
        parcel = transfer.parcel
        
        self._add_field(canvas, "Parcel ID:", parcel.parcel_id, 1*inch, y_position)
        self._add_field(canvas, "Title Number:", transfer.title.title_number, 
                       4*inch, y_position)
        
        y_position -= 0.25*inch
        self._add_field(canvas, "Location:", parcel.location, 1*inch, y_position)
        
        y_position -= 0.25*inch
        self._add_field(canvas, "District:", parcel.district, 1*inch, y_position)
        self._add_field(canvas, "Sector:", parcel.sector, 4*inch, y_position)
        
        y_position -= 0.25*inch
        self._add_field(canvas, "Property Type:", 
                       parcel.get_property_type_display(), 
                       1*inch, y_position)
        self._add_field(canvas, "Size:", f"{parcel.size_hectares} hectares", 
                       4*inch, y_position)
    
    def _add_declaration(self, canvas, transfer):
        """Add legal declaration"""
        y_position = 4.5*inch
        
        # Declaration box
        canvas.setFillColor(colors.HexColor('#f5f5f5'))
        canvas.rect(0.8*inch, y_position - 1.2*inch, 
                   self.page_width - 1.6*inch, 1.2*inch, 
                   fill=1, stroke=1)
        
        # Declaration text
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(1*inch, y_position - 0.3*inch, "DECLARATION:")
        
        canvas.setFont("Helvetica", 9)
        declaration_text = [
            "This is to certify that the ownership of the above-described property has been legally",
            f"transferred from {transfer.current_owner.get_full_name()} to {transfer.new_owner.get_full_name()}",
            "in accordance with the laws and regulations of the Democratic Republic of Congo.",
            "",
            "This transfer has been duly registered in the Digital Land Registry Management System",
            "and all necessary verifications have been completed."
        ]
        
        y_pos = y_position - 0.5*inch
        for line in declaration_text:
            canvas.drawString(1*inch, y_pos, line)
            y_pos -= 0.15*inch
        
        # Add review notes if any
        if transfer.review_notes:
            y_pos -= 0.1*inch
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(1*inch, y_pos, "Additional Notes:")
            canvas.setFont("Helvetica", 9)
            y_pos -= 0.15*inch
            # Wrap long notes
            words = transfer.review_notes.split()
            line = ""
            for word in words:
                if len(line + word) < 80:
                    line += word + " "
                else:
                    canvas.drawString(1*inch, y_pos, line.strip())
                    y_pos -= 0.15*inch
                    line = word + " "
            if line:
                canvas.drawString(1*inch, y_pos, line.strip())
    
    def _add_signatures_section(self, canvas, transfer, notary):
        """Add official signatures section"""
        y_position = 2.5*inch
        
        # Signature boxes
        # Notary signature (left)
        canvas.setFont("Helvetica", 10)
        canvas.line(1*inch, y_position, 3*inch, y_position)
        canvas.drawString(1*inch, y_position - 0.2*inch, notary.get_full_name())
        canvas.drawString(1*inch, y_position - 0.35*inch, "Notary Public")
        canvas.drawString(1*inch, y_position - 0.5*inch, 
                         f"License No: {getattr(notary, 'license_number', 'N/A')}")
        
        # Date and place (right)
        canvas.line(4.5*inch, y_position, 6.5*inch, y_position)
        canvas.drawString(4.5*inch, y_position - 0.2*inch, "Place: Kigali")
        canvas.drawString(4.5*inch, y_position - 0.35*inch, 
                         f"Date: {datetime.now().strftime('%B %d, %Y')}")
        
        # Official seal image
        seal_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'seal.png')
        if os.path.exists(seal_path):
            # Position the seal centered below the signatures
            seal_size = 1.5*inch
            seal_x = (self.page_width - seal_size) / 2
            seal_y = y_position - 1.5*inch
            
            canvas.drawImage(seal_path, seal_x, seal_y, 
                           width=seal_size, height=seal_size, 
                           preserveAspectRatio=True, mask='auto')
    
    def _add_field(self, canvas, label, value, x, y):
        """Add a field with label and value"""
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(x, y, label)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(x + 1.5*inch, y, str(value))
    
    def _add_section_header(self, canvas, text, y):
        """Add a section header with underline"""
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.HexColor('#000080'))
        canvas.drawString(1*inch, y, text)
        # Underline
        canvas.setLineWidth(0.5)
        canvas.line(1*inch, y - 2, 1*inch + len(text) * 6, y - 2)
        canvas.setFillColor(colors.black)
    
    def _add_footer(self, canvas, transfer):
        """Add footer with verification info and legal text"""
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        
        y_position = 0.8*inch
        
        # Verification info
        canvas.drawCentredString(self.page_width/2, y_position,
                               "This certificate is generated electronically and is valid without physical signature")
        y_position -= 0.15*inch
        canvas.drawCentredString(self.page_width/2, y_position,
                               "as per the Digital Land Registry Act of the Democratic Republic of Congo")
        y_position -= 0.15*inch
        canvas.drawCentredString(self.page_width/2, y_position,
                               f"Verify authenticity at: dlrms.gov.cd/verify/transfer/{transfer.transfer_number}")