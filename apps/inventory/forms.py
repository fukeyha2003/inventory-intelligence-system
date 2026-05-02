from django import forms
from django.contrib.auth.models import User
from .models import Company, UserProfile
from django.utils.text import slugify


class CompanySignupForm(forms.Form):
    """Custom signup form that captures company name"""
    company_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Company Name (e.g. Furor Fashion)'
        })
    )