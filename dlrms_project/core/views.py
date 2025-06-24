# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from applications.models import ParcelApplication, ParcelTitle
from disputes.models import Dispute

User = get_user_model()

class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['user'] = user
        context['unread_notifications_count'] = user.notifications.filter(is_read=False).count()

        # Surveyor-specific context
        if user.role == 'surveyor':
            from documents.models import Document

            # Applications assigned for field inspection
            assigned_applications = ParcelApplication.objects.filter(
                field_agent=user,
                status='field_inspection'
            ).select_related('applicant').order_by('-submitted_at')
            
            # Disputes assigned to surveyor for investigation or mediation
            assigned_disputes = Dispute.objects.filter(
                assigned_officer=user,
                status__in=['under_investigation', 'mediation'],
                dispute_type__in=['boundary', 'encroachment']
            ).select_related('parcel', 'complainant').order_by('-filed_at')  # Make sure `filed_at` exists
            
            context.update({
                'assigned_applications': assigned_applications,
                'pending_inspections_count': assigned_applications.count(),
                'assigned_disputes': assigned_disputes,
                'assigned_disputes_count': assigned_disputes.count(),
                'completed_inspections': ParcelApplication.objects.filter(
                    field_agent=user,
                    status__in=['approved', 'rejected']
                ).order_by('-review_date')[:5],
                'completed_inspections_count': ParcelApplication.objects.filter(
                    field_agent=user,
                    status__in=['approved', 'rejected']
                ).count(),
            })

        # Notary-specific context
        elif user.role == 'notary':
            from documents.models import Document
            from land_management.models import OwnershipTransfer
            from signatures.models import DigitalSignature
            
            pending_documents = Document.objects.filter(
                document_type__in=['transfer_agreement', 'legal_document'],
                is_verified=False
            ).select_related('uploaded_by').order_by('-uploaded_at')
            
            active_transfers = OwnershipTransfer.objects.filter(
                notary_required=True,
                status__in=['initiated', 'pending_approval']
            ).select_related('current_owner', 'new_owner', 'parcel').order_by('-initiated_at')
            
            recent_notarizations = DigitalSignature.objects.filter(
                signer=user,
                document_type__in=['transfer_agreement', 'legal_document'],
                status='signed'
            ).select_related('related_document').order_by('-signed_at')[:10]
            
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            context.update({
                'pending_documents': pending_documents[:5],
                'pending_notarization_count': pending_documents.count(),
                
                'active_transfers': active_transfers[:4],
                'active_transfers_count': active_transfers.count(),
                
                'notarized_today_count': DigitalSignature.objects.filter(
                    signer=user,
                    signed_at__date=today,
                    status='signed'
                ).count(),
                
                'notarized_this_month': DigitalSignature.objects.filter(
                    signer=user,
                    signed_at__date__gte=month_start,
                    status='signed'
                ).count(),
                
                'recent_notarizations': recent_notarizations,
                
                'weekly_count': DigitalSignature.objects.filter(
                    signer=user,
                    signed_at__date__gte=today - timezone.timedelta(days=7),
                    status='signed'
                ).count(),
            })

        # Landowner or other roles
        else:
            context['recent_applications'] = ParcelApplication.objects.filter(applicant=user).order_by('-submitted_at')[:4]
            context['recent_parcels'] = user.land_parcels.all().order_by('-created_at')[:3]
            
            context['pending_applications_count'] = ParcelApplication.objects.filter(
                applicant=user, 
                status__in=['submitted', 'under_review', 'field_inspection']
            ).count()
            
            context['parcel_titles_count'] = ParcelTitle.objects.filter(
                owner=user,
                is_active=True
            ).count()
        
        context['today'] = timezone.now().date()

        # Admin and Registry Officer stats
        if user.role in ['admin', 'registry_officer']:
            all_users = User.objects.all()
            context['total_users'] = all_users.count()
            context['verified_users'] = all_users.filter(is_verified=True).count()
            context['unverified_users'] = all_users.filter(is_verified=False).count()
            context['total_landowners'] = all_users.filter(role='landowner').count()
            context['total_officers'] = all_users.filter(
                role__in=['registry_officer', 'surveyor', 'notary', 'admin']
            ).count()
            context['recent_users'] = all_users.order_by('-date_joined')[:20]

            # Dispute statistics
            context['total_disputes'] = Dispute.objects.count()
            context['open_disputes'] = Dispute.objects.filter(status='open').count()
            context['resolved_disputes'] = Dispute.objects.filter(status='resolved').count()
            context['recent_disputes'] = Dispute.objects.order_by('-filed_at')[:5]

        return context


class AboutView(TemplateView):
    template_name = 'about.html'

class ServicesView(TemplateView):
    template_name = 'services.html'

class ContactView(TemplateView):
    template_name = 'contact.html'