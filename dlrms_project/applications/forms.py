# applications/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import ParcelApplication, ParcelDocument
from land_management.models import LandParcel

class ParcelApplicationForm(forms.ModelForm):
    """Form for submitting a parcel application"""
    
    # Document uploads
    owner_id = forms.FileField(label="Owner's ID (Document Upload)", required=True)
    sale_deed = forms.FileField(label="Sale Deed (Proof of land purchase)", required=True)
    previous_contract = forms.FileField(label="Previous Property Contract (if applicable)", required=False)
    
    # Property type choices
    PROPERTY_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('agricultural', 'Agricultural'),
        ('industrial', 'Industrial'),
        ('mixed', 'Mixed Use'),
    ]
    
    property_type = forms.ChoiceField(choices=PROPERTY_TYPE_CHOICES, label="Type of Property")
    
    class Meta:
        model = ParcelApplication
        fields = [
            'owner_first_name', 
            'owner_last_name', 
            'property_address',
            'property_type', 
            'application_type'
        ]
        widgets = {
            'owner_first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'property_address': forms.TextInput(attrs={'class': 'form-control'}),
            'application_type': forms.RadioSelect(),
        }
        labels = {
            'owner_first_name': "Owner's First Name",
            'owner_last_name': "Owner's Last Name",
            'property_address': "Property Address",
            'application_type': "Application Type",
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Customize application_type field
        self.fields['application_type'].choices = [
            ('property_contract', 'Property Contract (valid for 3 years)'),
            ('parcel_certificate', 'Parcel Certificate (lifetime validity)'),
        ]
        
        # Add Bootstrap classes to file inputs
        self.fields['owner_id'].widget.attrs.update({'class': 'form-control'})
        self.fields['sale_deed'].widget.attrs.update({'class': 'form-control'})
        self.fields['previous_contract'].widget.attrs.update({'class': 'form-control'})
        
        # Set help text for the previous_contract field
        self.fields['previous_contract'].help_text = "Only required if applying for a Parcel Certificate with a previous Property Contract"
    
    def clean(self):
        cleaned_data = super().clean()
        application_type = cleaned_data.get('application_type')
        previous_contract = cleaned_data.get('previous_contract')
        
        # No validation needed for missing fields as they're handled by the required attribute
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the applicant to the current user
        if self.user:
            instance.applicant = self.user
        
        if commit:
            instance.save()
            
            # Save the documents
            if 'owner_id' in self.cleaned_data:
                ParcelDocument.objects.create(
                    application=instance,
                    document_type='owner_id',
                    file=self.cleaned_data['owner_id']
                )
            
            if 'sale_deed' in self.cleaned_data:
                ParcelDocument.objects.create(
                    application=instance,
                    document_type='sale_deed',
                    file=self.cleaned_data['sale_deed']
                )
            
            if 'previous_contract' in self.cleaned_data and self.cleaned_data['previous_contract']:
                ParcelDocument.objects.create(
                    application=instance,
                    document_type='previous_contract',
                    file=self.cleaned_data['previous_contract']
                )
        
        return instance


class ApplicationAssignmentForm(forms.Form):
    """Form for registry officers to assign field agents to applications"""
    
    field_agent = forms.ModelChoiceField(
        queryset=None,
        label="Assign Field Agent",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get users with 'surveyor' role for field inspection
        User = LandParcel.owner.field.related_model
        self.fields['field_agent'].queryset = User.objects.filter(role='surveyor')


class ApplicationReviewForm(forms.Form):
    """Form for reviewing applications"""
    
    DECISION_CHOICES = [
        ('approve', 'Approve Application'),
        ('reject', 'Reject Application'),
    ]
    
    decision = forms.ChoiceField(
        choices=DECISION_CHOICES, 
        widget=forms.RadioSelect,
        label="Review Decision"
    )
    
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Review Notes",
        required=False
    )
    
    # Field inspection data
    latitude = forms.DecimalField(
        max_digits=10, 
        decimal_places=7,
        label="Property Latitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'})
    )
    
    longitude = forms.DecimalField(
        max_digits=10, 
        decimal_places=7,
        label="Property Longitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'})
    )
    
    size_hectares = forms.DecimalField(
        max_digits=10, 
        decimal_places=4,
        label="Property Size (hectares)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'})
    )