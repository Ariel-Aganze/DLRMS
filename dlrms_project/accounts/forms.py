from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Row, Column, HTML

User = get_user_model()

class CustomUserRegistrationForm(UserCreationForm):
    """Custom user registration form with additional fields"""
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    national_id = forms.CharField(max_length=50, required=False)
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 
            'phone_number', 'address', 'date_of_birth', 
            'national_id', 'password1', 'password2'
        )
        # Remove 'role' from fields - it will be set automatically to 'landowner'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        
        # Customize field widgets and classes
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })
        
        # Add placeholders for better UX
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a username'
        self.fields['email'].widget.attrs['placeholder'] = 'your.email@example.com'
        self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'
        self.fields['phone_number'].widget.attrs['placeholder'] = '+250 XXX XXX XXX'
        self.fields['national_id'].widget.attrs['placeholder'] = 'National ID number'
        self.fields['password1'].widget.attrs['placeholder'] = 'Choose a strong password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm your password'
        
        self.helper.layout = Layout(
            HTML('<h2 class="text-2xl font-bold text-gray-900 mb-6">Create Your DLRMS Account</h2>'),
            HTML('<p class="text-sm text-gray-600 mb-6">Join DLRMS as a landowner to manage your land registration and documentation.</p>'),
            
            Row(
                Column('first_name', css_class='w-full md:w-1/2 pr-2'),
                Column('last_name', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Row(
                Column('username', css_class='w-full md:w-1/2 pr-2'),
                Column('email', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Row(
                Column('phone_number', css_class='w-full md:w-1/2 pr-2'),
                Column('date_of_birth', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Field('national_id'),
            Field('address'),
            
            Row(
                Column('password1', css_class='w-full md:w-1/2 pr-2'),
                Column('password2', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Submit('submit', 'Create Account', 
                   css_class='w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 font-medium transition duration-200')
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data.get('phone_number')
        user.address = self.cleaned_data.get('address')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.national_id = self.cleaned_data.get('national_id')
        
        # Automatically set role to 'landowner' for public registration
        user.role = 'landowner'
        
        if commit:
            user.save()
        return user


class CustomLoginForm(AuthenticationForm):
    """Custom login form with styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        
        # Style the fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Username or Email'
        })
        
        self.fields['password'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Password'
        })
        
        self.helper.layout = Layout(
            HTML('<h2 class="text-2xl font-bold text-gray-900 mb-6">Login to DLRMS</h2>'),
            HTML('<p class="text-sm text-gray-600 mb-6">Enter your credentials to access your account.</p>'),
            
            Field('username'),
            Field('password'),
            
            HTML('''
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <input id="remember_me" name="remember_me" type="checkbox" class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded">
                        <label for="remember_me" class="ml-2 block text-sm text-gray-900">Remember me</label>
                    </div>
                    <div class="text-sm">
                        <a href="{% url 'accounts:password_reset' %}" class="font-medium text-blue-600 hover:text-blue-500">
                            Forgot your password?
                        </a>
                    </div>
                </div>
            '''),
            
            Submit('submit', 'Sign In', 
                   css_class='w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 font-medium transition duration-200'),
            
            HTML('''
                <div class="text-center">
                    <span class="text-sm text-gray-600">Don't have an account? </span>
                    <a href="{% url 'accounts:register' %}" class="text-sm font-medium text-blue-600 hover:text-blue-500">
                        Register here
                    </a>
                </div>
            ''')
        )


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'phone_number',
            'address', 'date_of_birth', 'national_id'
        )
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-6'
        
        # Style all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })
        
        self.helper.layout = Layout(
            HTML('<h2 class="text-2xl font-bold text-gray-900 mb-6">Update Profile</h2>'),
            
            Row(
                Column('first_name', css_class='w-full md:w-1/2 pr-2'),
                Column('last_name', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Field('email'),
            
            Row(
                Column('phone_number', css_class='w-full md:w-1/2 pr-2'),
                Column('date_of_birth', css_class='w-full md:w-1/2 pl-2'),
                css_class='flex flex-wrap -mx-2'
            ),
            
            Field('national_id'),
            Field('address'),
            
            Submit('submit', 'Update Profile', 
                   css_class='bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 font-medium transition duration-200')
        )


# Admin form for creating users with different roles
class AdminUserCreationForm(UserCreationForm):
    """Form for admins to create users with any role"""
    
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 
            'role', 'phone_number', 'address', 'date_of_birth', 
            'national_id', 'password1', 'password2', 'is_verified'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show staff/officer roles for admin creation
        self.fields['role'].choices = [
            ('registry_officer', 'Registry Officer'),
            ('surveyor', 'Surveyor'),
            ('notary', 'Notary'),
            ('admin', 'Administrator'),
            ('landowner', 'Landowner'),  # Include landowner for completeness
        ]