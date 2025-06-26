from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Dispute, DisputeComment, DisputeEvidence, MediationSession
from land_management.models import LandParcel

User = get_user_model()

class DisputeForm(forms.ModelForm):
    """Form for filing a new dispute"""
    
    class Meta:
        model = Dispute
        # Replace 'respondent' with 'respondent_name'
        fields = ['title', 'description', 'dispute_type', 'parcel', 'respondent_name']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Brief title of the dispute'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Provide detailed description of the dispute'
            }),
            'dispute_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'parcel': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            # Change the widget from Select to TextInput
            'respondent_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter the name of the person you are disputing with'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Only show parcels that the user owns or has disputes with
            self.fields['parcel'].queryset = LandParcel.objects.filter(
                Q(owner=user) | Q(disputes__complainant=user)
            ).distinct()


class DisputeCommentForm(forms.ModelForm):
    """Form for adding comments to disputes"""
    
    class Meta:
        model = DisputeComment
        fields = ['comment', 'is_internal']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Add your comment...'
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }


class DisputeEvidenceForm(forms.ModelForm):
    """Form for submitting evidence"""
    
    class Meta:
        model = DisputeEvidence
        fields = ['title', 'description', 'evidence_type', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Evidence title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Describe the evidence'
            }),
            'evidence_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
        }


class DisputeAssignmentForm(forms.ModelForm):
    """Form for assigning disputes to officers"""
    
    class Meta:
        model = Dispute
        fields = ['assigned_officer', 'priority']
        widgets = {
            'assigned_officer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Include notaries in the assignee list along with registry officers and admins
        self.fields['assigned_officer'].queryset = User.objects.filter(
            role__in=['registry_officer', 'admin', 'notary']
        )


class DisputeResolutionForm(forms.ModelForm):
    """Form for resolving disputes"""
    
    class Meta:
        model = Dispute
        fields = ['status', 'resolution', 'investigation_notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'resolution': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Describe the resolution...'
            }),
            'investigation_notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Investigation findings and notes...'
            }),
        }


class MediationSessionForm(forms.ModelForm):
    """Form for scheduling mediation sessions"""
    
    class Meta:
        model = MediationSession
        fields = ['scheduled_date', 'location', 'mediator']
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Mediation location'
            }),
            'mediator': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Include notaries as potential mediators along with officers
        self.fields['mediator'].queryset = User.objects.filter(
            role__in=['registry_officer', 'admin', 'notary']
        )