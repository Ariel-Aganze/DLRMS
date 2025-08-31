from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import ApproachEffectiveness, Dispute, DisputeComment, DisputeEvidence, MediationSession
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
        # SIMPLE FIX: Just show parcels owned by the user
        # Remove the problematic reverse relationship query
            self.fields['parcel'].queryset = LandParcel.objects.filter(owner=user)
        else:
        # If no user provided, show no parcels
            self.fields['parcel'].queryset = LandParcel.objects.none()


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


class DisputeOfficerAssignmentForm(forms.ModelForm):
    """Enhanced form for Dispute Officers to assign disputes with approach guidance"""
    
    class Meta:
        model = Dispute
        fields = ['assigned_officer', 'priority', 'suggested_approach', 'approach_notes']
        widgets = {
            'assigned_officer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500'
            }),
            'suggested_approach': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'id': 'id_suggested_approach'
            }),
            'approach_notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Provide specific guidance for the assigned officer (e.g., key points to investigate, parties\' availability, previous attempts, cultural considerations)'
            }),
        }
        labels = {
            'assigned_officer': 'Assign To',
            'priority': 'Priority Level',
            'suggested_approach': 'Resolution Approach (Optional)',
            'approach_notes': 'Guidance Notes (Optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Include notaries, surveyors for technical disputes, and registry officers
        self.fields['assigned_officer'].queryset = User.objects.filter(
            role__in=['registry_officer', 'notary', 'surveyor']
        ).order_by('role', 'first_name', 'last_name')
        
        # Make suggested_approach not required
        self.fields['suggested_approach'].required = False
        self.fields['approach_notes'].required = False
        
        # Add empty option for suggested_approach
        self.fields['suggested_approach'].empty_label = "-- No specific approach (Officer decides) --"


# ADD THIS HELPER CLASS FOR APPROACH RECOMMENDATIONS
class DisputeApproachRecommender:
    """Helper class to recommend resolution approaches based on dispute characteristics"""
    
    @staticmethod
    def recommend_approach(dispute):
        """Generate smart recommendations based on dispute type and characteristics"""
        recommendations = []
        
        # Based on dispute type
        if dispute.dispute_type == 'boundary':
            recommendations.append({
                'approach': 'technical_investigation',
                'reason': 'Boundary disputes typically require survey verification and technical assessment',
                'priority': 1
            })
            recommendations.append({
                'approach': 'site_inspection',
                'reason': 'Physical verification of boundaries often necessary',
                'priority': 2
            })
            
        elif dispute.dispute_type == 'inheritance':
            recommendations.append({
                'approach': 'documentary_review',
                'reason': 'Inheritance cases require thorough examination of wills and succession documents',
                'priority': 1
            })
            recommendations.append({
                'approach': 'multi_party_conference',
                'reason': 'Multiple family members typically need to be involved',
                'priority': 2
            })
            
        elif dispute.dispute_type == 'fraud':
            recommendations.append({
                'approach': 'complex_investigation',
                'reason': 'Fraud cases require detailed investigation and evidence gathering',
                'priority': 1
            })
            recommendations.append({
                'approach': 'documentary_review',
                'reason': 'Document authenticity verification is crucial',
                'priority': 2
            })
            
        elif dispute.dispute_type == 'ownership':
            recommendations.append({
                'approach': 'documentary_review',
                'reason': 'Ownership disputes require verification of title documents',
                'priority': 1
            })
            recommendations.append({
                'approach': 'direct_mediation',
                'reason': 'Direct discussion can clarify ownership claims',
                'priority': 3
            })
            
        elif dispute.dispute_type == 'encroachment':
            recommendations.append({
                'approach': 'site_inspection',
                'reason': 'Physical verification of encroachment is essential',
                'priority': 1
            })
            recommendations.append({
                'approach': 'technical_investigation',
                'reason': 'Survey measurements needed to confirm encroachment',
                'priority': 2
            })
        
        # Based on priority level
        if dispute.priority == 'urgent':
            recommendations.append({
                'approach': 'fast_track',
                'reason': 'Urgent cases require expedited resolution',
                'priority': 0  # Highest priority
            })
        elif dispute.priority == 'low':
            recommendations.append({
                'approach': 'direct_mediation',
                'reason': 'Low priority cases may be resolved through simple mediation',
                'priority': 3
            })
        
        # Check for repeat disputes between parties
        if dispute.complainant and dispute.respondent:
            previous_disputes = Dispute.objects.filter(
                complainant=dispute.complainant,
                respondent=dispute.respondent
            ).exclude(id=dispute.id if dispute.id else None).exists()
            
            if previous_disputes:
                recommendations.append({
                    'approach': 'shuttle_mediation',
                    'reason': 'Parties have dispute history - separate meetings recommended to avoid conflict',
                    'priority': 1
                })
        
        # Sort by priority (lower number = higher priority)
        recommendations.sort(key=lambda x: x['priority'])
        
        # Get effectiveness data if available
        for rec in recommendations:
            try:
                effectiveness = ApproachEffectiveness.objects.get(
                    dispute_type=dispute.dispute_type,
                    approach=rec['approach']
                )
                rec['success_rate'] = effectiveness.success_rate
                rec['average_days'] = effectiveness.average_resolution_days
            except ApproachEffectiveness.DoesNotExist:
                rec['success_rate'] = None
                rec['average_days'] = None
        
        return recommendations
    
    @staticmethod
    def get_approach_template(dispute_type, approach):
        """Get template guidance text for specific dispute type and approach combinations"""
        templates = {
            ('boundary', 'technical_investigation'): """
1. Request certified surveyor inspection within 7 days
2. Review historical parcel boundary records
3. Check for any registered easements or encumbrances
4. Compare current situation with original allocation documents
5. Schedule joint site visit with both parties present
6. Prepare boundary verification report
7. Draft boundary agreement if discrepancies found
            """,
            ('inheritance', 'multi_party_conference'): """
1. Identify and notify all potential heirs
2. Request death certificate and will (if available)
3. Review applicable succession laws (customary or statutory)
4. Verify family tree and relationships
5. Schedule family conference with neutral venue
6. Document all claims and objections
7. Facilitate consensus or identify specific disputes
8. Consider cultural and traditional practices
            """,
            ('fraud', 'complex_investigation'): """
1. Immediately freeze any pending transactions
2. Request all original documents for verification
3. Conduct handwriting/signature analysis if needed
4. Review complete transaction history
5. Interview all parties and witnesses separately
6. Check for similar fraud patterns in the system
7. Coordinate with law enforcement if criminal
8. Prepare detailed investigation report
            """,
            ('encroachment', 'site_inspection'): """
1. Schedule site inspection with both parties
2. Document current structures and boundaries
3. Take photographs and measurements
4. Compare with official parcel maps
5. Identify extent and duration of encroachment
6. Assess any improvements or developments
7. Explore possible solutions (adjustment, compensation)
8. Draft site inspection report with recommendations
            """,
        }
        
        return templates.get((dispute_type, approach), "")