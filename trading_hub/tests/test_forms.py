from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from trading_hub.forms import (
    KYCForm, AddressForm, BankAccountForm, 
    WireTransferForm, PriceAlertForm, TaxReportForm
)
from trading_hub.models import BankAccount

class KYCFormTest(TestCase):
    def test_kyc_form_valid_data(self):
        """Test KYCForm with valid data"""
        form_data = {
            'document_type': 'passport',
            'document_number': 'AB123456',
            'address_line1': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'postal_code': '12345',
            'country': 'USA'
        }
        form = KYCForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_kyc_form_missing_data(self):
        """Test KYCForm with missing required fields"""
        form_data = {
            'document_type': 'passport',
            # Missing document_number
            'address_line1': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'postal_code': '12345',
            'country': 'USA'
        }
        form = KYCForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('document_number', form.errors)

class AddressFormTest(TestCase):
    def test_address_form_valid_data(self):
        """Test AddressForm with valid data"""
        form_data = {
            'address_line1': '123 Main St',
            'address_line2': 'Apt 4B',
            'city': 'Anytown',
            'state': 'CA',
            'postal_code': '12345',
            'country': 'USA'
        }
        form = AddressForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_address_form_minimal_data(self):
        """Test AddressForm with minimal required data"""
        form_data = {
            'address_line1': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'postal_code': '12345',
            'country': 'USA'
        }
        form = AddressForm(data=form_data)
        self.assertTrue(form.is_valid())

class BankAccountFormTest(TestCase):
    def test_bank_account_form_valid_data(self):
        """Test BankAccountForm with valid data"""
        form_data = {
            'bank_name': 'Test Bank',
            'account_number': '12345678',
            'routing_number': '123456789',
            'account_type': 'checking',
            'account_holder_name': 'John Doe'
        }
        form = BankAccountForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_bank_account_form_missing_data(self):
        """Test BankAccountForm with missing required fields"""
        form_data = {
            'bank_name': 'Test Bank',
            # Missing account_number
            'routing_number': '123456789',
            'account_type': 'checking'
            # Missing account_holder_name
        }
        form = BankAccountForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('account_number', form.errors)
        self.assertIn('account_holder_name', form.errors)

class WireTransferFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.bank_account = BankAccount.objects.create(
            user=self.user,
            bank_name='Test Bank',
            account_number='12345678',
            routing_number='123456789',
            account_type='checking',
            account_holder_name='John Doe'
        )
    
    def test_wire_transfer_form_init(self):
        """Test WireTransferForm initialization with user"""
        form = WireTransferForm(user=self.user)
        self.assertEqual(form.fields['bank_account'].queryset.count(), 1)
        self.assertEqual(form.fields['bank_account'].queryset.first(), self.bank_account)
    
    def test_wire_transfer_form_valid_data(self):
        """Test WireTransferForm with valid data"""
        form_data = {
            'amount': '1000.00',
            'bank_account': self.bank_account.id
        }
        form = WireTransferForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_wire_transfer_form_negative_amount(self):
        """Test WireTransferForm with negative amount"""
        form_data = {
            'amount': '-100.00',
            'bank_account': self.bank_account.id
        }
        form = WireTransferForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

class PriceAlertFormTest(TestCase):
    def test_price_alert_form_valid_data(self):
        """Test PriceAlertForm with valid data"""
        form_data = {
            'symbol': 'BTC',
            'target_price': '50000.00'
        }
        form = PriceAlertForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_price_alert_form_missing_data(self):
        """Test PriceAlertForm with missing required fields"""
        form_data = {
            'symbol': 'BTC'
            # Missing target_price
        }
        form = PriceAlertForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('target_price', form.errors)

class TaxReportFormTest(TestCase):
    def test_tax_report_form_valid_data(self):
        """Test TaxReportForm with valid data"""
        current_year = timezone.now().year
        form_data = {
            'tax_year': current_year,
            'cost_basis_method': 'fifo',
            'report_format': 'csv',
            'include_unrealized_gains': False
        }
        form = TaxReportForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_tax_report_form_defaults(self):
        """Test TaxReportForm default values"""
        form = TaxReportForm()
        self.assertEqual(form.fields['tax_year'].initial, timezone.now().year)
        self.assertEqual(form.fields['cost_basis_method'].initial, 'fifo')
        self.assertEqual(form.fields['report_format'].initial, 'csv')
        self.assertFalse(form.fields['include_unrealized_gains'].initial)
