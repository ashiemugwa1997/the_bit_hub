from django import forms
from .models import KYC, BankAccount, PriceAlert
from django.utils import timezone

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = [
            'document_type', 'document_number', 'document_image', 
            'address_line1', 'address_line2', 'city', 'state', 
            'postal_code', 'country'
        ]
        exclude = ['user', 'status', 'rejection_reason', 'submitted_at', 
                  'verified_at', 'address_rejection_reason', 'tier']

class AddressForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ['address_line1', 'address_line2', 'city', 'state', 
                 'postal_code', 'country']

class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        exclude = ['user', 'created_at', 'updated_at', 'verified']

class WireTransferForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, label='Amount (USD)')
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), label='Bank Account')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user)

class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ['symbol', 'target_price']

class TaxReportForm(forms.Form):
    tax_year = forms.IntegerField(
        label="Tax Year", 
        initial=timezone.now().year,
        widget=forms.Select(choices=[(year, year) for year in range(2020, timezone.now().year + 1)])
    )
    
    cost_basis_method = forms.ChoiceField(
        label="Cost Basis Method",
        choices=[
            ('fifo', 'First In, First Out (FIFO)'),
            ('lifo', 'Last In, First Out (LIFO)'),
            ('hifo', 'Highest In, First Out (HIFO)'),
            ('acb', 'Average Cost Basis (ACB)')
        ],
        initial='fifo',
        help_text="Method used to calculate cost basis for your crypto assets"
    )
    
    report_format = forms.ChoiceField(
        label="Report Format",
        choices=[
            ('csv', 'CSV'),
            ('pdf', 'PDF'),
            ('turbotax', 'TurboTax Compatible')
        ],
        initial='csv'
    )
    
    include_unrealized_gains = forms.BooleanField(
        label="Include Unrealized Gains",
        required=False,
        initial=False,
        help_text="Include potential gains/losses from assets you still hold"
    )
