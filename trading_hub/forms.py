from django import forms
from .models import KYC
from .models import BankAccount

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ['document_type', 'document_number', 'document_file', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country']

class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['account_number', 'bank_name', 'account_holder_name', 'ifsc_code']

class WireTransferForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, label='Amount (USD)')
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects.none(), label='Bank Account')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user)
