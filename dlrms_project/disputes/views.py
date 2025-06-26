from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required

from accounts.admin import User


from .models import Dispute, DisputeComment, DisputeEvidence, DisputeTimeline, MediationSession
from .forms import (
    DisputeForm, DisputeCommentForm, DisputeEvidenceForm, 
    DisputeAssignmentForm, DisputeResolutionForm, MediationSessionForm
)
from core.mixins import RoleRequiredMixin

class DisputeListView(LoginRequiredMixin, ListView):
    """List view for disputes based on user role"""
    model = Dispute
    template_name = 'disputes/dispute_list.html'
    context_object_name = 'disputes'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Dispute.objects.select_related('complainant', 'respondent', 'parcel', 'assigned_officer')
        user = self.request.user
        
        # Filter based on user role
        if user.role == 'landowner':
            # Landowners see only their disputes
            queryset = queryset.filter(
                Q(complainant=user) | Q(respondent=user)
            )
        elif user.role == 'surveyor':
            # Surveyors see disputes assigned to them for investigation
            queryset = queryset.filter(
                assigned_officer=user,
                dispute_type__in=['boundary', 'encroachment']
            )
        elif user.role == 'notary':
            # Notaries see only disputes assigned to them
            queryset = queryset.filter(assigned_officer=user)
        elif user.role in ['registry_officer', 'admin']:
            # Officers and admins see all disputes
            pass
        else:
            # Other roles see no disputes
            queryset = queryset.none()
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        dispute_type = self.request.GET.get('type')
        if dispute_type:
            queryset = queryset.filter(dispute_type=dispute_type)
        
        return queryset.order_by('-filed_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Dispute.DISPUTE_STATUS_CHOICES
        context['type_choices'] = Dispute.DISPUTE_TYPE_CHOICES
        return context


class DisputeCreateView(LoginRequiredMixin, CreateView):
    """Create a new dispute"""
    model = Dispute
    form_class = DisputeForm
    template_name = 'disputes/dispute_create.html'
    success_url = reverse_lazy('disputes:dispute_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        dispute = form.save(commit=False)
        dispute.complainant = self.request.user
        dispute.save()
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Dispute Filed',
            description=f'Dispute filed by {self.request.user.get_full_name()}',
            created_by=self.request.user
        )
        
        messages.success(self.request, 'Dispute has been filed successfully.')
        return super().form_valid(form)


class DisputeDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a dispute"""
    model = Dispute
    template_name = 'disputes/dispute_detail.html'
    context_object_name = 'dispute'
    
    def get_object(self):
        dispute = super().get_object()
        user = self.request.user
        
        # Check permissions
        if user.role == 'landowner':
            if dispute.complainant != user and dispute.respondent != user:
                raise HttpResponseForbidden("You don't have permission to view this dispute.")
        elif user.role in ['surveyor', 'notary']:
            if dispute.assigned_officer != user:
                raise HttpResponseForbidden("You don't have permission to view this dispute.")
        
        return dispute
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dispute = self.object
        
        # Add forms to context
        context['comment_form'] = DisputeCommentForm()
        context['evidence_form'] = DisputeEvidenceForm()
        
        # Add related data
        context['comments'] = dispute.comments.select_related('author')
        context['evidence'] = dispute.evidence.select_related('submitted_by')
        context['timeline'] = dispute.timeline.select_related('created_by')
        context['mediation_sessions'] = dispute.mediation_sessions.select_related('mediator')
        
        if self.request.user.role in ['registry_officer', 'admin', 'notary']:
            context['available_mediators'] = User.objects.filter(
                role__in=['registry_officer', 'admin', 'notary']
            )

        # Filter internal comments for non-officers
        if self.request.user.role not in ['registry_officer', 'admin', 'notary']:
            context['comments'] = context['comments'].filter(is_internal=False)
        
        return context


class DisputeResolveView(RoleRequiredMixin, UpdateView):
    """Resolve a dispute - for officers and notaries"""
    model = Dispute
    form_class = DisputeResolutionForm
    template_name = 'disputes/dispute_resolve.html'
    allowed_roles = ['registry_officer', 'admin', 'notary']
    
    def form_valid(self, form):
        dispute = form.save(commit=False)
        
        if dispute.status == 'resolved':
            dispute.resolution_date = timezone.now()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                dispute=dispute,
                event='Dispute Resolved',
                description=f'Dispute resolved by {self.request.user.get_full_name()}',
                created_by=self.request.user
            )
            
            messages.success(self.request, 'Dispute has been resolved successfully.')
        else:
            messages.success(self.request, 'Dispute status updated successfully.')
        
        dispute.save()
        return redirect('disputes:dispute_detail', pk=dispute.pk)


class DisputeAssignView(RoleRequiredMixin, UpdateView):
    """Assign dispute to an officer"""
    model = Dispute
    form_class = DisputeAssignmentForm
    template_name = 'disputes/dispute_assign.html'
    allowed_roles = ['registry_officer', 'admin']
    
    def form_valid(self, form):
        dispute = form.save()
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Officer Assigned',
            description=f'Dispute assigned to {dispute.assigned_officer.get_full_name()} by {self.request.user.get_full_name()}',
            created_by=self.request.user
        )
        
        # Update status if needed
        if dispute.status == 'submitted':
            dispute.status = 'under_investigation'
            dispute.save()
        
        messages.success(self.request, f'Dispute assigned to {dispute.assigned_officer.get_full_name()} successfully.')
        return redirect('disputes:dispute_detail', pk=dispute.pk)


# Ajax views for adding comments and evidence
def add_comment(request, pk):
    """Add comment to dispute via AJAX"""
    if request.method == 'POST' and request.user.is_authenticated:
        dispute = get_object_or_404(Dispute, pk=pk)
        
        # Check permissions
        user = request.user
        if user.role == 'landowner':
            if dispute.complainant != user and dispute.respondent != user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        form = DisputeCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.dispute = dispute
            comment.author = request.user
            
            # Only officers and notaries can post internal comments
            if request.user.role not in ['registry_officer', 'admin', 'notary']:
                comment.is_internal = False
            
            comment.save()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                dispute=dispute,
                event='Comment Added',
                description=f'Comment added by {request.user.get_full_name()}',
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'author': comment.author.get_full_name(),
                    'comment': comment.comment,
                    'created_at': comment.created_at.strftime('%B %d, %Y at %I:%M %p'),
                    'is_internal': comment.is_internal
                }
            })
        else:
            return JsonResponse({'error': 'Invalid form data'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def add_evidence(request, pk):
    """Add evidence to dispute via AJAX"""
    if request.method == 'POST' and request.user.is_authenticated:
        dispute = get_object_or_404(Dispute, pk=pk)
        
        # Check permissions
        user = request.user
        if user.role == 'landowner':
            if dispute.complainant != user and dispute.respondent != user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        form = DisputeEvidenceForm(request.POST, request.FILES)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.dispute = dispute
            evidence.submitted_by = request.user
            evidence.save()
            
            # Create timeline entry
            DisputeTimeline.objects.create(
                dispute=dispute,
                event='Evidence Submitted',
                description=f'{evidence.title} submitted by {request.user.get_full_name()}',
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'evidence': {
                    'title': evidence.title,
                    'description': evidence.description,
                    'evidence_type': evidence.get_evidence_type_display(),
                    'submitted_by': evidence.submitted_by.get_full_name(),
                    'submitted_at': evidence.submitted_at.strftime('%B %d, %Y at %I:%M %p'),
                    'file_url': evidence.file.url if evidence.file else None
                }
            })
        else:
            return JsonResponse({'error': 'Invalid form data'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def schedule_mediation(request, pk):
    """Schedule a mediation session for a dispute"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})

    # Check user role
    if request.user.role not in ['registry_officer', 'admin', 'notary']:
        return HttpResponseForbidden("You don't have permission to schedule mediation sessions.")

    dispute = get_object_or_404(Dispute, pk=pk)
    
    # Create mediation session
    form = MediationSessionForm(request.POST)
    if form.is_valid():
        session = form.save(commit=False)
        session.dispute = dispute
        session.save()
        
        # Update dispute status to mediation if not already
        if dispute.status != 'mediation':
            dispute.status = 'mediation'
            dispute.save()
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Mediation Scheduled',
            description=f'Mediation session scheduled for {session.scheduled_date.strftime("%B %d, %Y at %I:%M %p")} at {session.location}',
            created_by=request.user
        )
        
        messages.success(request, 'Mediation session scheduled successfully.')
        return redirect('disputes:dispute_detail', pk=dispute.pk)
    else:
        messages.error(request, 'Error scheduling mediation session. Please check the form data.')
        return redirect('disputes:dispute_detail', pk=dispute.pk)