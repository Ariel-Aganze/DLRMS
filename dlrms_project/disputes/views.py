from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
import json

from accounts.models import User
from notifications.models import Notification
from .models import (
    Dispute, DisputeComment, DisputeEvidence, DisputeTimeline, 
    MediationSession, ApproachEffectiveness
)
from .forms import (
    DisputeForm, DisputeCommentForm, DisputeEvidenceForm, 
    DisputeAssignmentForm, DisputeResolutionForm, MediationSessionForm,
    DisputeOfficerAssignmentForm, DisputeApproachRecommender
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
            queryset = queryset.filter(
                Q(complainant=user) | Q(respondent=user)
            )
        elif user.role == 'surveyor':
            queryset = queryset.filter(
                assigned_officer=user,
                dispute_type__in=['boundary', 'encroachment']
            )
        elif user.role == 'notary':
            queryset = queryset.filter(assigned_officer=user)
        elif user.role in ['registry_officer', 'admin', 'dispute_officer']:  # ADD dispute_officer
            # Officers, admins, and dispute officers see all disputes
            pass
        else:
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
        
        # Add statistics for dispute officers
        if self.request.user.role == 'dispute_officer':
            context['unassigned_count'] = Dispute.objects.filter(
                assigned_officer__isnull=True,
                status='submitted'
            ).count()
            context['urgent_count'] = Dispute.objects.filter(
                priority='urgent',
                status__in=['submitted', 'under_investigation']
            ).count()
        
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
        # dispute_officer, registry_officer, and admin can view all disputes
        
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
        
        if self.request.user.role in ['registry_officer', 'admin', 'notary', 'dispute_officer']:
            context['available_mediators'] = User.objects.filter(
                role__in=['registry_officer', 'admin', 'notary']
            )
        
        # Filter internal comments for non-officers
        if self.request.user.role not in ['registry_officer', 'admin', 'notary', 'dispute_officer']:
            context['comments'] = context['comments'].filter(is_internal=False)
        
        # Add approach guidance visibility
        context['show_approach_guidance'] = (
            dispute.suggested_approach and 
            self.request.user.role in ['notary', 'surveyor', 'registry_officer', 'admin', 'dispute_officer']
        )
        
        return context


class DisputeResolveView(RoleRequiredMixin, UpdateView):
    """Resolve a dispute - for officers, notaries, and dispute officers"""
    model = Dispute
    form_class = DisputeResolutionForm
    template_name = 'disputes/dispute_resolve.html'
    allowed_roles = ['registry_officer', 'admin', 'notary', 'dispute_officer']  # ADD dispute_officer here
    
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


class DisputeOfficerAssignView(RoleRequiredMixin, UpdateView):
    """Enhanced assignment view for Dispute Officers with approach guidance"""
    model = Dispute
    form_class = DisputeOfficerAssignmentForm
    template_name = 'disputes/dispute_officer_assign.html'
    allowed_roles = ['dispute_officer', 'admin']
    
    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing the request"""
        self.object = self.get_object()
        
        # Check if user has permission
        if request.user.role not in self.allowed_roles:
            messages.error(request, "You don't have permission to assign disputes.")
            return redirect('disputes:dispute_detail', pk=self.object.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        """Get the dispute object"""
        return get_object_or_404(Dispute, pk=self.kwargs['pk'])
    
    def get_form_kwargs(self):
        """Pass additional kwargs to the form"""
        kwargs = super().get_form_kwargs()
        # You can add additional context to the form here if needed
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add context data for the template"""
        context = super().get_context_data(**kwargs)
        dispute = self.object
        
        # Get smart recommendations using the recommender
        recommender = DisputeApproachRecommender()
        recommendations = recommender.recommend_approach(dispute)
        
        # Format the recommendations for display (to avoid template filter issues)
        for rec in recommendations:
            # Add a properly formatted display name
            approach_display = rec['approach'].replace('_', ' ').title()
            rec['approach_display'] = approach_display
        
        context['recommendations'] = recommendations
        
        # Get approach templates and format them
        context['approach_templates'] = {}
        for approach_choice in Dispute.RESOLUTION_APPROACH_CHOICES:
            template_text = recommender.get_approach_template(
                dispute.dispute_type, 
                approach_choice[0]
            )
            if template_text:
                context['approach_templates'][approach_choice[0]] = template_text
        
        # Get available officers with their current workload
        officers = User.objects.filter(
            role__in=['notary', 'surveyor', 'registry_officer']
        ).annotate(
            active_disputes=Count('assigned_disputes', 
                filter=Q(assigned_disputes__status__in=['under_investigation', 'mediation']))
        ).order_by('active_disputes')
        
        context['officers_workload'] = officers
        
        # Add dispute type choices for JavaScript
        context['dispute_type'] = dispute.dispute_type
        
        # Add current user info
        context['current_user'] = self.request.user
        
        return context
    
    def form_valid(self, form):
        """Handle valid form submission"""
        dispute = form.save(commit=False)
        
        # Track who suggested the approach and when
        if form.cleaned_data.get('suggested_approach'):
            dispute.approach_suggested_by = self.request.user
            dispute.approach_suggested_at = timezone.now()
        
        # Save the dispute with updated information
        dispute.save()
        
        # Build event description for timeline
        event_description = f'Dispute assigned to {dispute.assigned_officer.get_full_name()} by {self.request.user.get_full_name()}'
        
        # Add approach information if provided
        if dispute.suggested_approach:
            event_description += f' with {dispute.get_suggested_approach_display()} approach'
        
        # Add priority information
        event_description += f'. Priority: {dispute.get_priority_display()}'
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Officer Assigned with Guidance',
            description=event_description,
            created_by=self.request.user
        )
        
        # Update dispute status if it's still in submitted state
        if dispute.status == 'submitted':
            dispute.status = 'under_investigation'
            dispute.save()
            
            # Create additional timeline entry for status change
            DisputeTimeline.objects.create(
                dispute=dispute,
                event='Status Changed',
                description='Status changed from Submitted to Under Investigation',
                created_by=self.request.user
            )
        
        # Send notification to assigned officer
        from notifications.models import Notification
        if dispute.assigned_officer:
            # Build notification message
            notification_message = f'You have been assigned dispute {dispute.dispute_number} ({dispute.get_dispute_type_display()}). '
            notification_message += f'Priority: {dispute.get_priority_display()}. '
            
            if dispute.suggested_approach:
                notification_message += f'Suggested approach: {dispute.get_suggested_approach_display()}. '
            
            if dispute.approach_notes:
                notification_message += 'Please review the guidance notes provided.'
            
            Notification.objects.create(
                recipient=dispute.assigned_officer,
                title='New Dispute Assignment',
                message=notification_message,
                notification_type='dispute_assignment',
                related_dispute=dispute
            )
            
            # Also notify the complainant that an officer has been assigned
            Notification.objects.create(
                recipient=dispute.complainant,
                title='Officer Assigned to Your Dispute',
                message=f'An officer has been assigned to investigate your dispute {dispute.dispute_number}.',
                notification_type='dispute_status',
                related_dispute=dispute
            )
        
        # Show success message
        messages.success(
            self.request, 
            f'Dispute {dispute.dispute_number} has been assigned to {dispute.assigned_officer.get_full_name()} successfully.'
        )
        
        # Log the assignment
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Dispute {dispute.dispute_number} assigned to {dispute.assigned_officer.username} by {self.request.user.username}')
        
        # Redirect to dispute detail page
        return redirect('disputes:dispute_detail', pk=dispute.pk)
    
    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        """Get the URL to redirect to after successful form submission"""
        return reverse_lazy('disputes:dispute_detail', kwargs={'pk': self.object.pk})

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
    

@login_required
def get_approach_recommendations(request, pk):
    """AJAX view to get approach recommendations for a dispute"""
    if request.user.role not in ['dispute_officer', 'admin']:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    dispute = get_object_or_404(Dispute, pk=pk)
    recommender = DisputeApproachRecommender()
    recommendations = recommender.recommend_approach(dispute)
    
    # Format for JSON response
    formatted_recommendations = []
    for rec in recommendations:
        formatted_rec = {
            'approach': rec['approach'],
            'approach_display': dict(Dispute.RESOLUTION_APPROACH_CHOICES).get(rec['approach']),
            'reason': rec['reason'],
            'priority': rec['priority']
        }
        if rec.get('success_rate') is not None:
            formatted_rec['success_rate'] = f"{rec['success_rate']:.1f}%"
        if rec.get('average_days') is not None:
            formatted_rec['average_days'] = rec['average_days']
        formatted_recommendations.append(formatted_rec)
    
    return JsonResponse({'recommendations': formatted_recommendations})


# ADD AJAX endpoint for getting approach template
@login_required
def get_approach_template(request):
    """AJAX view to get template text for a specific approach"""
    if request.user.role not in ['dispute_officer', 'admin', 'notary', 'registry_officer']:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    dispute_type = request.GET.get('dispute_type')
    approach = request.GET.get('approach')
    
    if not dispute_type or not approach:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    recommender = DisputeApproachRecommender()
    template_text = recommender.get_approach_template(dispute_type, approach)
    
    return JsonResponse({'template': template_text})

@require_POST
@login_required
def guidance_feedback(request, pk):
    """Record feedback on approach guidance helpfulness"""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    # Only assigned officer can provide feedback
    if dispute.assigned_officer != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        is_helpful = data.get('helpful', False)
        
        # Update approach effectiveness if it was helpful and resolved
        if is_helpful and dispute.status == 'resolved' and dispute.suggested_approach:
            effectiveness, created = ApproachEffectiveness.objects.get_or_create(
                dispute_type=dispute.dispute_type,
                approach=dispute.suggested_approach,
                defaults={'success_count': 0, 'total_count': 0}
            )
            
            if is_helpful:
                effectiveness.success_count += 1
            effectiveness.total_count += 1
            
            # Calculate average resolution days
            if dispute.resolution_date and dispute.filed_at:
                days_to_resolve = (dispute.resolution_date - dispute.filed_at).days
                current_avg = effectiveness.average_resolution_days
                new_avg = ((current_avg * (effectiveness.total_count - 1)) + days_to_resolve) / effectiveness.total_count
                effectiveness.average_resolution_days = new_avg
            
            effectiveness.save()
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Approach Feedback',
            description=f'Officer found the suggested approach {"helpful" if is_helpful else "not helpful"}',
            created_by=request.user
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    

# DISPUTE MANAGEMENT AJAX VIEWS
@login_required
@require_POST
def update_dispute_status(request, pk):
    """AJAX view to update dispute status"""
    # Check permissions - allow dispute_officer, registry_officer, admin, and notary
    if request.user.role not in ['dispute_officer', 'registry_officer', 'admin', 'notary']:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to update dispute status.'
        }, status=403)
    
    try:
        dispute = get_object_or_404(Dispute, pk=pk)
        data = json.loads(request.body)
        
        # Get the new status
        new_status = data.get('status')
        investigation_notes = data.get('investigation_notes', '')
        resolution = data.get('resolution', '')
        
        # Validate status
        valid_statuses = [choice[0] for choice in Dispute.DISPUTE_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status selected.'
            }, status=400)
        
        # Update the dispute
        old_status = dispute.status
        dispute.status = new_status
        
        # Add investigation notes if provided
        if investigation_notes:
            if dispute.investigation_notes:
                dispute.investigation_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {request.user.get_full_name()}:\n{investigation_notes}"
            else:
                dispute.investigation_notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {request.user.get_full_name()}:\n{investigation_notes}"
        
        # Handle resolution if status is resolved
        if new_status == 'resolved':
            if resolution:
                dispute.resolution = resolution
            dispute.resolution_date = timezone.now()
            
            # Create notification for parties
            from notifications.models import Notification
            for user in [dispute.complainant, dispute.respondent] if dispute.respondent else [dispute.complainant]:
                if user:
                    Notification.objects.create(
                        recipient=user,
                        title='Dispute Resolved',
                        message=f'Dispute {dispute.dispute_number} has been resolved.',
                        notification_type='dispute_status',
                        related_dispute=dispute
                    )
        
        dispute.save()
        
        # Create timeline entry
        DisputeTimeline.objects.create(
            dispute=dispute,
            event='Status Updated',
            description=f'Status changed from {old_status} to {new_status} by {request.user.get_full_name()}',
            created_by=request.user
        )
        
        # If assigned officer exists and status changed to under_investigation, notify them
        if dispute.assigned_officer and new_status == 'under_investigation' and old_status != 'under_investigation':
            from notifications.models import Notification
            Notification.objects.create(
                recipient=dispute.assigned_officer,
                title='Dispute Assignment Active',
                message=f'Dispute {dispute.dispute_number} is now under investigation.',
                notification_type='dispute_assignment'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Dispute status updated to {dispute.get_status_display()}',
            'new_status': new_status,
            'new_status_display': dispute.get_status_display()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request data.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)