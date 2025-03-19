from django import forms
from trading_hub.models import APIKey
from datetime import datetime, timedelta
from django.utils import timezone

class APIKeyForm(forms.ModelForm):
    EXPIRY_CHOICES = [
        (30, '30 days'),
        (60, '60 days'),
        (90, '90 days'),
        (180, '180 days'),
        (365, '365 days'),
        (0, 'No expiry'),
    ]
    
    expiry_days = forms.ChoiceField(
        choices=EXPIRY_CHOICES, 
        label="Key Expiration", 
        initial=30, 
        required=True
    )
    
    class Meta:
        model = APIKey
        fields = ['name', 'permissions', 'allowed_ips']
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set expiry date based on choice
        expiry_days = int(self.cleaned_data['expiry_days'])
        if expiry_days > 0:
            instance.expires_at = timezone.now() + timedelta(days=expiry_days)
        else:
            instance.expires_at = None
            
        if commit:
            instance.save()
            
        return instance