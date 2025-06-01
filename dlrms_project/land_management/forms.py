from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Row, Column, HTML, Div
from .models import ParcelApplication, LandParcel

class ParcelApplicationForm(forms.ModelForm):
    """Form for submitting parcel registration applications"""
    
    class Meta:
        model = ParcelApplication
        fields = [
            'application_type',
            'owner_first_name',
            'owner_last_name',
            'property_address',
            'property_type',
            'owner_id_document',
            'sale_deed_document',
            'previous_contract_document',
        ]
        
        widgets = {
            'owner_first_name': forms.TextInput(attrs={
                'placeholder': 'Enter owner\'s first name',
                'class': 'form-control'
            }),
            'owner_last_name': forms.TextInput(attrs={
                'placeholder': 'Enter owner\'s last name',
                'class': 'form-control'
            }),
            'property_address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter complete property address',
                'class': 'form-control'
            }),
            'application_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_application_type'
            }),
            'property_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'owner_id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'sale_deed_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'previous_contract_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make previous_contract_document optional initially
        self.fields['previous_contract_document'].required = False
        
        # Set up crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'space-y-6'
        
        # Custom layout
        self.helper.layout = Layout(
            HTML('''
                <div class="bg-white shadow-lg rounded-lg p-6 mb-6">
                    <h2 class="text-2xl font-bold text-gray-900 mb-4">
                        <svg class="inline-block w-6 h-6 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        Submit Parcel Registration Application
                    </h2>
                    <p class="text-gray-600 mb-6">Complete this form to register your property and obtain either a Property Contract or Parcel Certificate.</p>
                </div>
            '''),
            
            # Application Type Section
            Div(
                HTML('<h3 class="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Application Type</h3>'),
                Div(
                    Field('application_type', css_class='w-full'),
                    HTML('''
                        <div class="mt-2 text-sm text-gray-600">
                            <div class="bg-blue-50 p-3 rounded-lg">
                                <p><strong>Property Contract:</strong> Valid for 3 years, renewable</p>
                                <p><strong>Parcel Certificate:</strong> Lifetime validity, permanent ownership document</p>
                            </div>
                        </div>
                    '''),
                    css_class='mb-6'
                ),
                css_class='bg-white shadow rounded-lg p-6 mb-6'
            ),
            
            # Owner Information Section
            Div(
                HTML('<h3 class="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Owner Information</h3>'),
                Row(
                    Column('owner_first_name', css_class='form-group col-md-6 mb-4'),
                    Column('owner_last_name', css_class='form-group col-md-6 mb-4'),
                    css_class='form-row'
                ),
                css_class='bg-white shadow rounded-lg p-6 mb-6'
            ),
            
            # Property Information Section
            Div(
                HTML('<h3 class="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Property Information</h3>'),
                Field('property_address', css_class='mb-4'),
                Field('property_type', css_class='mb-4'),
                css_class='bg-white shadow rounded-lg p-6 mb-6'
            ),
            
            # Required Documents Section
            Div(
                HTML('<h3 class="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Required Documents</h3>'),
                HTML('''
                    <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p class="text-sm text-yellow-800">
                            <svg class="inline-block w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                            </svg>
                            Please ensure all documents are clear and readable. Accepted formats: PDF, JPG, PNG (Max 10MB each)
                        </p>
                    </div>
                '''),
                
                Div(
                    HTML('<label class="block text-sm font-medium text-gray-700 mb-2">Owner\'s ID Document *</label>'),
                    Field('owner_id_document', css_class='mb-1'),
                    HTML('<p class="text-xs text-gray-500">Upload a clear copy of your national ID or passport</p>'),
                    css_class='mb-4'
                ),
                
                Div(
                    HTML('<label class="block text-sm font-medium text-gray-700 mb-2">Sale Deed Document *</label>'),
                    Field('sale_deed_document', css_class='mb-1'),
                    HTML('<p class="text-xs text-gray-500">Upload the official sale deed or proof of purchase</p>'),
                    css_class='mb-4'
                ),
                
                # Conditional field for previous contract
                Div(
                    HTML('<label class="block text-sm font-medium text-gray-700 mb-2">Previous Property Contract (Optional)</label>'),
                    Field('previous_contract_document', css_class='mb-1'),
                    HTML('''
                        <p class="text-xs text-gray-500">
                            If you have a previous property contract for this parcel, upload it here. 
                            This field is only relevant for Parcel Certificate applications.
                        </p>
                    '''),
                    css_class='mb-4',
                    css_id='previous_contract_field',
                    style='display: none;'  # Initially hidden
                ),
                
                css_class='bg-white shadow rounded-lg p-6 mb-6'
            ),
            
            # Terms and Conditions
            HTML('''
                <div class="bg-white shadow rounded-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">Terms and Conditions</h3>
                    <div class="space-y-3 text-sm text-gray-600">
                        <label class="flex items-start">
                            <input type="checkbox" name="terms_accepted" required class="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                            <span>I hereby declare that all information provided is true and accurate. I understand that providing false information may result in rejection of my application and potential legal consequences.</span>
                        </label>
                        <label class="flex items-start">
                            <input type="checkbox" name="document_authenticity" required class="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                            <span>I confirm that all uploaded documents are authentic and have not been altered or falsified.</span>
                        </label>
                        <label class="flex items-start">
                            <input type="checkbox" name="processing_consent" required class="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                            <span>I consent to the processing of my personal data for the purpose of land registration and agree to field inspection of the property if required.</span>
                        </label>
                    </div>
                </div>
            '''),
            
            # Submit Button
            Div(
                HTML('''
                    <div class="flex items-center justify-between">
                        <a href="{% url 'land_management:dashboard' %}" class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
                            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16l-4-4m0 0l4-4m-4 4h18"></path>
                            </svg>
                            Cancel
                        </a>
                '''),
                Submit('submit', 'Submit Application', 
                       css_class='inline-flex items-center px-6 py-2 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors'),
                HTML('</div>'),
                css_class='bg-white shadow rounded-lg p-6'
            ),
            
            # JavaScript for conditional field display
            HTML('''
                <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const applicationTypeField = document.getElementById('id_application_type');
                    const previousContractField = document.getElementById('previous_contract_field');
                    
                    function togglePreviousContractField() {
                        if (applicationTypeField.value === 'certificate') {
                            previousContractField.style.display = 'block';
                        } else {
                            previousContractField.style.display = 'none';
                            // Clear the field when hidden
                            const fileInput = previousContractField.querySelector('input[type="file"]');
                            if (fileInput) {
                                fileInput.value = '';
                            }
                        }
                    }
                    
                    // Initial check
                    togglePreviousContractField();
                    
                    // Listen for changes
                    applicationTypeField.addEventListener('change', togglePreviousContractField);
                });
                </script>
            ''')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        application_type = cleaned_data.get('application_type')
        owner_first_name = cleaned_data.get('owner_first_name')
        owner_last_name = cleaned_data.get('owner_last_name')
        
        # Validate file sizes
        for field_name in ['owner_id_document', 'sale_deed_document', 'previous_contract_document']:
            file_field = cleaned_data.get(field_name)
            if file_field and hasattr(file_field, 'size'):
                if file_field.size > 10 * 1024 * 1024:
                    raise ValidationError(f'{field_name}: File size must be less than 10MB')
        
        # Validate that user information matches authenticated user if provided
        if self.user:
            if (owner_first_name and owner_first_name.lower() != self.user.first_name.lower()):
                self.add_error('owner_first_name', 'First name must match your account information')
            
            if (owner_last_name and owner_last_name.lower() != self.user.last_name.lower()):
                self.add_error('owner_last_name', 'Last name must match your account information')
        
        return cleaned_data
    
    def clean_owner_id_document(self):
        file = self.cleaned_data['owner_id_document']
        if file:
            # Validate file type
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError('Only PDF, JPG, and PNG files are allowed for ID documents')
        return file
    
    def clean_sale_deed_document(self):
        file = self.cleaned_data['sale_deed_document']
        if file:
            # Validate file type
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError('Only PDF, JPG, and PNG files are allowed for sale deed documents')
        return file