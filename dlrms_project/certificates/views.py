from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.http import HttpResponse, JsonResponse, Http404
from django.core.files.base import ContentFile
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
import json
import hashlib

from .models import Certificate, CertificateAuditLog
from .generator import CertificateGenerator
from applications.models import ParcelApplication
from signatures.models import DigitalSignature
from notifications.models import Notification
from accounts.models import User


class CertificateListView(LoginRequiredMixin, ListView):
    """List certificates for the logged-in user"""
    model = Certificate
    template_name = 'certificates/certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Certificate.objects.filter(status='issued')
        
        # Filter based on user role
        if self.request.user.role == 'landowner':
            queryset = queryset.filter(owner=self.request.user)
        elif self.request.user.role in ['registry_officer', 'admin']:
            # Can see all certificates
            pass
        else:
            # Other roles see no certificates by default
            queryset = queryset.none()
        
        # Apply search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(certificate_number__icontains=search)
        
        return queryset.select_related('owner', 'application')



class GenerateCertificateView(LoginRequiredMixin, View):
    """Generate certificate for approved application"""
    
    def get(self, request, application_id):
        """Show signature page before generating certificate"""
        # Check permissions
        if request.user.role not in ['registry_officer', 'admin']:
            messages.error(request, 'You do not have permission to generate certificates.')
            return redirect('applications:application_detail', pk=application_id)
        
        # Get the application
        application = get_object_or_404(ParcelApplication, pk=application_id)
        
        # Check if application is approved
        if application.status != 'approved':
            messages.error(request, 'Only approved applications can have certificates generated.')
            return redirect('applications:application_detail', pk=application_id)
        
        # Check if certificate already exists
        if hasattr(application, 'certificate'):
            messages.info(request, 'Certificate already exists for this application.')
            return redirect('certificates:certificate_detail', pk=application.certificate.pk)
        
        # Render signature collection page
        context = {
            'application': application,
            'signer': request.user
        }
        return render(request, 'certificates/pre_sign_certificate.html', context)
    
    def post(self, request, application_id):
        """Generate certificate with signature"""
        # Check permissions
        if request.user.role not in ['registry_officer', 'admin']:
            messages.error(request, 'You do not have permission to generate certificates.')
            return redirect('applications:application_detail', pk=application_id)
        
        # Get the application
        application = get_object_or_404(ParcelApplication, pk=application_id)
        
        # Get signature data from POST
        signature_data = request.POST.get('signature_data')
        if not signature_data:
            # messages.error(request, 'Please provide a signature before generating the certificate.')
            return redirect('certificates:generate_certificate', application_id=application_id)
        
        try:
            # Create certificate record
            certificate = Certificate.objects.create(
                application=application,
                owner=application.applicant,
                certificate_type=application.application_type,
                issued_by=request.user,
                issue_date=timezone.now()
            )
            
            # Calculate expiry date
            certificate.calculate_expiry_date()
            
            # Generate PDF with signature
            generator = CertificateGenerator()
            try:
                # Pass signature data to generator
                pdf_content, document_hash = generator.generate_certificate(
                    certificate, 
                    signature_data=signature_data,
                    signer_name=request.user.get_full_name(),
                    sign_date=timezone.now()
                )
            except Exception as pdf_error:
                # If PDF generation fails, delete the certificate and show error
                certificate.delete()
                messages.error(request, f'Error generating certificate PDF: {str(pdf_error)}')
                return redirect('applications:application_detail', pk=application_id)
            
            # Save PDF file
            certificate.pdf_file.save(
                f'certificate_{certificate.certificate_number}.pdf',
                ContentFile(pdf_content)
            )
            
            # Save document hash
            certificate.document_hash = document_hash
            certificate.status = 'issued'
            certificate.save()
            
            # Create digital signature record
            signature = DigitalSignature.objects.create(
                signer=request.user,
                document_type='application_approval',
                document_title=f'Certificate {certificate.certificate_number}',
                document_hash=document_hash,
                signature_hash=hashlib.sha256(signature_data.encode()).hexdigest(),
                signature_image=signature_data,
                certificate_serial=certificate.certificate_number,
                certificate_issuer='DRC Land Registry',
                certificate_valid_from=timezone.now(),
                certificate_valid_until=certificate.expiry_date,
                is_verified=True,
                verification_method='Pre-signing',
                verification_timestamp=timezone.now(),
                status='signed'
            )
            
            # Link signature to certificate
            certificate.signatures.add(signature)
            
            # Create audit log
            CertificateAuditLog.objects.create(
                certificate=certificate,
                action='created',
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'certificate_number': certificate.certificate_number, 'pre_signed': True}
            )
            
            # Create notifications
            notifications_to_create = []
            
            # 1. Notify the landowner that their certificate is ready
            notifications_to_create.append(
                Notification(
                    recipient=application.applicant,
                    title='Certificate Ready!',
                    message=f'Your {certificate.get_certificate_type_display()} certificate {certificate.certificate_number} has been generated and is ready for download.',
                    notification_type='document_uploaded',
                    priority='high',
                    sender=request.user
                )
            )
            
            # 2. Notify other registry officers and admin
            other_officers = User.objects.filter(
                role__in=['registry_officer', 'admin'], 
                is_active=True
            ).exclude(id=request.user.id)
            
            for officer in other_officers:
                notifications_to_create.append(
                    Notification(
                        recipient=officer,
                        title='Certificate Generated',
                        message=f'Certificate {certificate.certificate_number} has been generated for {application.applicant.get_full_name()} by {request.user.get_full_name()}',
                        notification_type='system_alert',
                        sender=request.user
                    )
                )
            
            # 3. If there was a field agent, notify them too
            if application.field_agent:
                notifications_to_create.append(
                    Notification(
                        recipient=application.field_agent,
                        title='Certificate Issued',
                        message=f'Certificate has been issued for application {application.application_number} that you inspected',
                        notification_type='system_alert',
                        sender=request.user
                    )
                )
            
            # Bulk create all notifications
            Notification.objects.bulk_create(notifications_to_create)
            
            messages.success(request, f'Certificate {certificate.certificate_number} has been generated successfully!')
            return redirect('applications:application_detail', pk=application_id)
            
        except Exception as e:
            messages.error(request, f'Error generating certificate: {str(e)}')
            return redirect('applications:application_detail', pk=application_id)


class CertificateDetailView(LoginRequiredMixin, DetailView):
    """View certificate details"""
    model = Certificate
    template_name = 'certificates/certificate_detail.html'
    context_object_name = 'certificate'
    
    def get_object(self):
        certificate = super().get_object()
        
        # Check permissions
        user = self.request.user
        if user.role == 'landowner' and certificate.owner != user:
            raise Http404("Certificate not found")
        
        # Log view action
        CertificateAuditLog.objects.create(
            certificate=certificate,
            action='viewed',
            performed_by=user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        return certificate
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['signatures'] = self.object.signatures.all()
        context['audit_logs'] = self.object.audit_logs.order_by('-timestamp')[:10]
        context['can_sign'] = self.request.user.role in ['registry_officer', 'admin', 'notary']
        return context


class DownloadCertificateView(LoginRequiredMixin, View):
    """Download certificate PDF"""
    
    def get(self, request, pk):
        certificate = get_object_or_404(Certificate, pk=pk)
        
        # Check permissions
        user = request.user
        if user.role == 'landowner' and certificate.owner != user:
            raise Http404("Certificate not found")
        
        # Check if PDF exists
        if not certificate.pdf_file:
            messages.error(request, 'Certificate PDF not found. Please regenerate the certificate.')
            return redirect('certificates:certificate_detail', pk=pk)
        
        # Check if this is the first download by the owner
        first_download_by_owner = False
        if user == certificate.owner:
            owner_downloads = CertificateAuditLog.objects.filter(
                certificate=certificate,
                action='downloaded',
                performed_by=user
            ).count()
            if owner_downloads == 0:
                first_download_by_owner = True
        
        # Log download action
        CertificateAuditLog.objects.create(
            certificate=certificate,
            action='downloaded',
            performed_by=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # If first download by owner, notify registry officers
        if first_download_by_owner:
            registry_officers = User.objects.filter(
                role__in=['registry_officer', 'admin'], 
                is_active=True
            )
            
            notifications_to_create = []
            for officer in registry_officers:
                notifications_to_create.append(
                    Notification(
                        recipient=officer,
                        title='Certificate Downloaded by Owner',
                        message=f'{user.get_full_name()} has downloaded their certificate {certificate.certificate_number} for the first time',
                        notification_type='system_alert',
                        sender=user
                    )
                )
            
            Notification.objects.bulk_create(notifications_to_create)
        
        # Serve the PDF
        response = HttpResponse(certificate.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
        return response



class VerifyCertificateView(View):
    """Public certificate verification - Enhanced to show details"""
    template_name = 'certificates/verify_certificate.html'
    
    def get(self, request, certificate_id=None):
        if certificate_id:
            try:
                certificate = Certificate.objects.get(certificate_id=certificate_id)
                
                # Log verification
                CertificateAuditLog.objects.create(
                    certificate=certificate,
                    action='verified',
                    performed_by=request.user if request.user.is_authenticated else None,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                context = {
                    'certificate': certificate,
                    'is_valid': certificate.is_valid,
                    'verification_success': True,
                    'certificate_id': certificate_id  # Add this to show details
                }
            except Certificate.DoesNotExist:
                context = {
                    'verification_success': False,
                    'error_message': 'Certificate not found'
                }
        else:
            context = {}
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Verify by certificate number - Enhanced to redirect with details"""
        certificate_number = request.POST.get('certificate_number', '').strip()
        
        if not certificate_number:
            return JsonResponse({'success': False, 'error': 'Certificate number is required'})
        
        try:
            certificate = Certificate.objects.select_related('owner', 'application').prefetch_related('signatures__signer').get(
                certificate_number=certificate_number
            )
            
            # Log verification
            CertificateAuditLog.objects.create(
                certificate=certificate,
                action='verified',
                performed_by=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Get additional details from the application if available
            application = certificate.application
            property_details = {
                'address': getattr(application, 'property_address', 'N/A'),
                'size': f"{getattr(application, 'size_hectares', 0)} hectares" if hasattr(application, 'size_hectares') else 'N/A',
                'use_type': getattr(application, 'intended_use', 'N/A'),
                'location': {
                    'district': getattr(application, 'district', 'N/A'),
                    'sector': getattr(application, 'sector', 'N/A'),
                    'cell': getattr(application, 'cell', 'N/A'),
                }
            }
            
            # Get digital signatures information
            signatures_data = []
            for signature in certificate.signatures.all():
                signatures_data.append({
                    'id': signature.id,
                    'signature_id': getattr(signature, 'signature_id', str(signature.id)),
                    'signer_name': signature.signer.get_full_name(),
                    'role': signature.signer.get_role_display(),
                    'signed_at': signature.signed_at.strftime('%B %d, %Y at %I:%M %p'),
                    'document_hash': getattr(signature, 'document_hash', ''),
                    'is_verified': getattr(signature, 'is_verified', True),
                })
            
            return JsonResponse({
                'success': True,
                'redirect': True,
                'redirect_url': request.build_absolute_uri(f'/certificates/verify/{certificate.certificate_id}/'),
                'certificate': {
                    'id': str(certificate.certificate_id),
                    'number': certificate.certificate_number,
                    'type': certificate.get_certificate_type_display(),
                    'owner': certificate.owner.get_full_name(),
                    'owner_email': certificate.owner.email,
                    'issue_date': certificate.issue_date.strftime('%B %d, %Y') if certificate.issue_date else 'Not issued',
                    'expiry_date': certificate.expiry_date.strftime('%B %d, %Y') if certificate.expiry_date else 'Lifetime',
                    'is_valid': certificate.is_valid,
                    'status': certificate.get_status_display(),
                    'property_details': property_details,
                    'signatures': signatures_data,  # Include signature information
                    'verification_url': request.build_absolute_uri(f'/certificates/verify/{certificate.certificate_id}/'),
                }
            })
        except Certificate.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Certificate not found. Please check the certificate number and try again.'
            })

class SignCertificateView(LoginRequiredMixin, View):
    """Add digital signature to certificate"""
    
    def post(self, request, pk):
        certificate = get_object_or_404(Certificate, pk=pk)
        
        # Check permissions
        if request.user.role not in ['registry_officer', 'admin', 'notary']:
            return JsonResponse({'success': False, 'error': 'Insufficient permissions'})
        
        # Get signature data
        signature_data = request.POST.get('signature_data')
        signature_type = request.POST.get('signature_type', 'approval')
        
        if not signature_data:
            return JsonResponse({'success': False, 'error': 'Signature data is required'})
        
        try:
            # Create digital signature
            signature = DigitalSignature.objects.create(
                signer=request.user,
                document_type='application_approval',
                document_title=f'Certificate {certificate.certificate_number}',
                document_hash=certificate.document_hash,
                signature_hash=hashlib.sha256(signature_data.encode()).hexdigest(),  # Store hash of signature
                signature_image=signature_data,  # Store actual signature image in new field
                related_document=None,
                certificate_serial=certificate.certificate_number,
                certificate_issuer='DRC Land Registry',
                certificate_valid_from=timezone.now(),
                certificate_valid_until=certificate.expiry_date,
                is_verified=True,
                verification_method='PKI',
                verification_timestamp=timezone.now(),
                status='signed',
                signature_metadata={
                    'signature_type': signature_type,
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')
                }
            )
            
            # Add signature to certificate
            certificate.signatures.add(signature)
            
            # Log the signing action
            CertificateAuditLog.objects.create(
                certificate=certificate,
                action='signed',
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'signature_id': str(signature.signature_id),
                    'signature_type': signature_type
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Certificate signed successfully',
                'signature_id': str(signature.signature_id)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})