from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.http import JsonResponse
from django.utils import timezone
from django.core.files.base import ContentFile
from django.urls import reverse_lazy
import json
import hashlib
from io import BytesIO

from .models import Certificate, CertificateAuditLog
from signatures.models import DigitalSignature
from documents.models import Document


class DocumentSigningView(LoginRequiredMixin, DetailView):
    """View for signing documents"""
    template_name = 'certificates/document_signing.html'
    context_object_name = 'document'
    
    def get_object(self):
        # This could be either a Certificate or a Document
        doc_type = self.kwargs.get('doc_type', 'certificate')
        doc_id = self.kwargs.get('doc_id')
        
        if doc_type == 'certificate':
            return get_object_or_404(Certificate, pk=doc_id)
        else:
            return get_object_or_404(Document, pk=doc_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc_type = self.kwargs.get('doc_type', 'certificate')
        
        context['doc_type'] = doc_type
        context['can_sign'] = self._can_sign()
        context['existing_signatures'] = self._get_existing_signatures()
        context['signature_positions'] = self._get_signature_positions()
        
        return context
    
    def _can_sign(self):
        """Check if current user can sign this document"""
        user = self.request.user
        doc_type = self.kwargs.get('doc_type', 'certificate')
        
        # Define signing permissions based on role and document type
        if doc_type == 'certificate':
            return user.role in ['registry_officer', 'admin', 'notary']
        else:
            # For other documents, check specific permissions
            return user.role in ['admin', 'registry_officer', 'notary', 'landowner']
    
    def _get_existing_signatures(self):
        """Get existing signatures for this document"""
        doc = self.get_object()
        
        if hasattr(doc, 'signatures'):
            return doc.signatures.all().select_related('signer')
        else:
            # For documents without direct signature relationship
            return DigitalSignature.objects.filter(
                document_hash=self._calculate_document_hash(doc)
            ).select_related('signer')
    
    def _get_signature_positions(self):
        """Define where signatures should appear on the document"""
        doc_type = self.kwargs.get('doc_type', 'certificate')
        
        if doc_type == 'certificate':
            return [
                {'id': 'registry_officer', 'label': 'Registry Officer', 'x': 100, 'y': 600},
                {'id': 'owner', 'label': 'Property Owner', 'x': 300, 'y': 600},
                {'id': 'witness', 'label': 'Witness', 'x': 500, 'y': 600},
            ]
        else:
            return [
                {'id': 'signer1', 'label': 'Primary Signer', 'x': 100, 'y': 600},
                {'id': 'signer2', 'label': 'Secondary Signer', 'x': 400, 'y': 600},
            ]
    
    def _calculate_document_hash(self, document):
        """Calculate SHA-256 hash of document content"""
        if hasattr(document, 'pdf_file') and document.pdf_file:
            content = document.pdf_file.read()
            document.pdf_file.seek(0)  # Reset file pointer
        else:
            # For documents without PDF, hash the key fields
            content = f"{document.pk}{document.created_at}".encode()
        
        return hashlib.sha256(content).hexdigest()


@login_required
def sign_document_ajax(request):
    """AJAX endpoint for signing documents"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        data = json.loads(request.body)
        doc_type = data.get('doc_type', 'certificate')
        doc_id = data.get('doc_id')
        signature_data = data.get('signature_data')
        signature_position = data.get('position', {})
        signature_type = data.get('signature_type', 'approval')
        
        # Get the document
        if doc_type == 'certificate':
            document = get_object_or_404(Certificate, pk=doc_id)
            document_title = f"Certificate {document.certificate_number}"
        else:
            document = get_object_or_404(Document, pk=doc_id)
            document_title = document.title or f"Document {document.pk}"
        
        # Calculate document hash
        document_hash = hashlib.sha256(
            f"{document.pk}{signature_data}".encode()
        ).hexdigest()
        
        # Create digital signature
        signature = DigitalSignature.objects.create(
            signer=request.user,
            document_type='application_approval' if doc_type == 'certificate' else 'legal_document',
            document_title=document_title,
            document_hash=document_hash,
            signature_hash=signature_data,
            status='signed',
            is_verified=True,
            verification_method='Browser-based signing',
            verification_timestamp=timezone.now()
        )
        
        # Add metadata
        if hasattr(signature, 'metadata'):
            signature.metadata = {
                'position': signature_position,
                'signature_type': signature_type,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
            signature.save()
        
        # Link signature to document if possible
        if hasattr(document, 'signatures'):
            document.signatures.add(signature)
        
        # Create audit log for certificates
        if doc_type == 'certificate':
            CertificateAuditLog.objects.create(
                certificate=document,
                action='signed',
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'signature_id': str(signature.signature_id),
                    'signature_type': signature_type,
                    'position': signature_position
                }
            )
        
        return JsonResponse({
            'success': True,
            'signature_id': str(signature.signature_id),
            'message': 'Document signed successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


class SignedDocumentsListView(LoginRequiredMixin, ListView):
    """List all documents signed by the user"""
    model = DigitalSignature
    template_name = 'certificates/signed_documents_list.html'
    context_object_name = 'signatures'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by current user
        queryset = queryset.filter(signer=self.request.user)
        
        # Apply filters
        doc_type = self.request.GET.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(signed_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(signed_at__lte=date_to)
        
        return queryset.order_by('-signed_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['document_types'] = DigitalSignature.DOCUMENT_TYPE_CHOICES
        context['status_choices'] = DigitalSignature.SIGNATURE_STATUS_CHOICES
        return context


@login_required
def verify_document_signature(request, signature_id):
    """Verify a document signature"""
    signature = get_object_or_404(DigitalSignature, signature_id=signature_id)
    
    # Perform verification
    is_valid = signature.is_verified and signature.status == 'signed'
    
    # Check if signature hasn't been revoked
    if signature.status == 'revoked':
        is_valid = False
        message = "This signature has been revoked."
    elif signature.status == 'invalid':
        is_valid = False
        message = "This signature is invalid."
    elif not signature.is_verified:
        is_valid = False
        message = "This signature could not be verified."
    else:
        message = "Signature is valid and verified."
    
    return JsonResponse({
        'success': True,
        'is_valid': is_valid,
        'message': message,
        'signature': {
            'id': str(signature.signature_id),
            'signer': signature.signer.get_full_name(),
            'signed_at': signature.signed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'document': signature.document_title,
            'status': signature.get_status_display()
        }
    })