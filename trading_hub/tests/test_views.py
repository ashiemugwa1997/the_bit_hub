from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import json

from trading_hub.models import (
    CryptoCurrency, Wallet, Transaction, LimitOrder, 
    StopOrder, RecurringOrder, TaxReport
)

class DashboardViewTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Create some wallets
        self.btc_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='BTC',
            name='Bitcoin Wallet',
            balance=Decimal('1.5'),
            address='btc-address-123'
        )
        
        self.eth_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='ETH',
            name='Ethereum Wallet',
            balance=Decimal('10.0'),
            address='eth-address-456'
        )
        
        self.usd_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            name='USD Wallet',
            balance=Decimal('5000.0'),
            address='usd-address-789'
        )
        
        # Create cryptocurrencies
        self.btc = CryptoCurrency.objects.create(
            code='BTC',
            name='Bitcoin',
            current_price_usd=Decimal('50000.00')
        )
        
        self.eth = CryptoCurrency.objects.create(
            code='ETH',
            name='Ethereum',
            current_price_usd=Decimal('3000.00')
        )
        
        # Create some transactions
        self.transaction = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('0.1'),
            currency='BTC',
            native_amount=Decimal('5000.00'),
            native_currency='USD',
            status='completed',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            description='Test purchase'
        )
    
    def test_dashboard_view_status(self):
        """Test dashboard view returns 200 status"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_context(self):
        """Test dashboard view contains correct context data"""
        response = self.client.get(reverse('dashboard'))
        
        # Check wallet data in context
        self.assertIn('wallet_data', response.context)
        wallet_data = response.context['wallet_data']
        self.assertEqual(len(wallet_data), 3)  # 3 wallets
        
        # Check portfolio value in context (BTC 1.5 * 50000 + ETH 10 * 3000 + USD 5000)
        expected_value = Decimal('1.5') * Decimal('50000.00') + Decimal('10.0') * Decimal('3000.00') + Decimal('5000.0')
        self.assertIn('portfolio_value', response.context)
        self.assertEqual(response.context['portfolio_value'], expected_value)
        
        # Check recent transactions in context
        self.assertIn('recent_transactions', response.context)
        self.assertEqual(len(response.context['recent_transactions']), 1)
    
    def test_dashboard_requires_login(self):
        """Test dashboard view requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

class AssetListViewTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Create cryptocurrencies
        self.btc = CryptoCurrency.objects.create(
            code='BTC',
            name='Bitcoin',
            current_price_usd=Decimal('50000.00')
        )
        
        self.eth = CryptoCurrency.objects.create(
            code='ETH',
            name='Ethereum',
            current_price_usd=Decimal('3000.00')
        )
        
        # Create a wallet for BTC
        self.btc_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='BTC',
            name='Bitcoin Wallet',
            balance=Decimal('1.5'),
            address='btc-address-123'
        )
    
    def test_asset_list_view_status(self):
        """Test asset list view returns 200 status"""
        response = self.client.get(reverse('asset_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_asset_list_context(self):
        """Test asset list view contains correct context data"""
        response = self.client.get(reverse('asset_list'))
        
        # Check crypto data in context
        self.assertIn('crypto_data', response.context)
        crypto_data = response.context['crypto_data']
        self.assertEqual(len(crypto_data), 2)  # 2 cryptocurrencies
        
        # Check that BTC shows has_balance=True and ETH shows has_balance=False
        btc_data = next(data for data in crypto_data if data['crypto'].code == 'BTC')
        eth_data = next(data for data in crypto_data if data['crypto'].code == 'ETH')
        
        self.assertTrue(btc_data['has_balance'])
        self.assertEqual(btc_data['balance'], Decimal('1.5'))
        self.assertEqual(btc_data['balance_usd'], Decimal('1.5') * Decimal('50000.00'))
        
        self.assertFalse(eth_data['has_balance'])
        self.assertEqual(eth_data['balance'], Decimal('0'))
        self.assertEqual(eth_data['balance_usd'], Decimal('0'))

# Additional test classes for other views...

class TaxCenterViewTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Create tax reports
        self.tax_report_2023 = TaxReport.objects.create(
            user=self.user,
            tax_year=2023,
            report_format='csv',
            status='completed'
        )
        
        self.tax_report_2022 = TaxReport.objects.create(
            user=self.user,
            tax_year=2022,
            report_format='pdf',
            status='completed'
        )
    
    def test_tax_center_view_status(self):
        """Test tax center view returns 200 status"""
        response = self.client.get(reverse('tax_center'))
        self.assertEqual(response.status_code, 200)
    
    def test_tax_center_context(self):
        """Test tax center view contains correct context data"""
        response = self.client.get(reverse('tax_center'))
        
        # Check reports in context
        self.assertIn('reports', response.context)
        reports = list(response.context['reports'])
        self.assertEqual(len(reports), 2)
        
        # Check reports are ordered by tax_year descending
        self.assertEqual(reports[0].tax_year, 2023)
        self.assertEqual(reports[1].tax_year, 2022)
        
        # Check tax years in context
        self.assertIn('tax_years', response.context)
        # Should include at least 2022, 2023, and current year
        self.assertTrue(2022 in response.context['tax_years'])
        self.assertTrue(2023 in response.context['tax_years'])
        self.assertTrue(timezone.now().year in response.context['tax_years'])
