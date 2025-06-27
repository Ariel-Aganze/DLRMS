from django import forms
from django.contrib.auth import get_user_model
from .models import OwnershipTransfer
from applications.models import ParcelTitle

User = get_user_model()

class TransferInitiationForm(forms.ModelForm):
    """Form for landowner to initiate transfer"""
    
    receiver_national_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter receiver\'s National ID',
            'id': 'receiver_national_id'
        })
    )
    
    confirm_receiver = forms.BooleanField(
        required=True,
        label='I confirm the receiver details are correct',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = OwnershipTransfer
        fields = [
            'reason', 'other_reason', 'transfer_value', 
            'sale_deed', 'current_owner_id_document',
            'receiver_national_id', 'receiver_first_name', 
            'receiver_last_name', 'receiver_phone', 'receiver_email'
        ]
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'other_reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Please specify if Other'
            }),
            'transfer_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transfer value (optional)'
            }),
            'receiver_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'receiver_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'receiver_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'receiver_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'sale_deed': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'current_owner_id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.parcel = kwargs.pop('parcel', None)
        self.title = kwargs.pop('title', None)
        super().__init__(*args, **kwargs)
        
        # Make other_reason required if reason is 'other'
        self.fields['other_reason'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        other_reason = cleaned_data.get('other_reason')
        
        if reason == 'other' and not other_reason:
            raise forms.ValidationError('Please specify the reason for transfer.')
        
        return cleaned_data


class ReceiverConfirmationForm(forms.ModelForm):
    """Form for receiver to confirm transfer"""
    
    confirm_transfer = forms.BooleanField(
        required=True,
        label='I confirm that I want to receive this land ownership',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = OwnershipTransfer
        fields = ['receiver_phone', 'receiver_email', 'new_owner_id_document']
        widgets = {
            'receiver_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'receiver_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'new_owner_id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make new_owner_id_document required
        self.fields['new_owner_id_document'].required = True


class TransferReviewForm(forms.ModelForm):
    """Form for notary to review transfer"""
    
    decision = forms.ChoiceField(
        choices=[('approved', 'Approve'), ('rejected', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = OwnershipTransfer
        fields = ['review_notes']
        widgets = {
            'review_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter review notes (visible to both parties)'
            })
        }