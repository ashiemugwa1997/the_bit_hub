from django import forms
from .models import KYC

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ['document_type', 'document_number', 'document_file', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country']
