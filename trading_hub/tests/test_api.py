from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import json
import uuid

from trading_hub.models import (
    CryptoCurrency, APIKey, Transaction, Wallet
)

class APIKeyAuthenticationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = Client()
        
        # Create API key
        self.api_key = APIKey.objects.create(
            user=self.user,
            name='Test API Key',
            permissions='read'
        )
        
        # API headers
        self.headers = {
            'HTTP_X_API_KEY': self.api_key.key,
            'HTTP_X_API_SECRET': self.api_key.secret
        }
    
    def test_api_key_authentication_success(self):
        """Test API key authentication succeeds with valid credentials"""
        # Test an API endpoint that requires authentication
        response = self.client.get(
            reverse('api_calculate_cost_basis'), 
            content_type='application/json',
            data=json.dumps({'crypto_code': 'BTC'}),
            **self.headers
        )
        # The API should return 400 for invalid data but not 401/403 for auth issues
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)
    
    def test_api_key_authentication_failure(self):
        """Test API key authentication fails with invalid credentials"""
        # Test with invalid key
        invalid_headers = {
            'HTTP_X_API_KEY': 'invalid-key',
            'HTTP_X_API_SECRET': self.api_key.secret
        }
        response = self.client.get(
            reverse('api_calculate_cost_basis'), 
            content_type='application/json',
            data=json.dumps({'crypto_code': 'BTC'}),
            **invalid_headers
        )
        self.assertEqual(response.status_code, 401)

class ConversionRateAPITest(TestCase):
    def setUp(self):
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
    
    def test_get_conversion_rate_success(self):
        """Test getting conversion rate between two cryptocurrencies"""
        response = self.client.get(
            reverse('get_conversion_rate', args=['BTC', 'ETH'])
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['from'], 'BTC')
        self.assertEqual(data['to'], 'ETH')
        # Expected rate: ETH price / BTC price = 3000 / 50000 = 0.06
        self.assertEqual(data['rate'], 0.06)
        self.assertIn('timestamp', data)
    
    def test_get_conversion_rate_invalid_crypto(self):
        """Test error handling for invalid cryptocurrency in conversion rate API"""
        response = self.client.get(
            reverse('get_conversion_rate', args=['BTC', 'INVALID'])
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)

class CalculateCostBasisAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
        
        # Create cryptocurrencies
        self.btc = CryptoCurrency.objects.create(
            code='BTC',
            name='Bitcoin',
            current_price_usd=Decimal('50000.00')
        )
        
        # Create wallets
        self.btc_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='BTC',
            balance=Decimal('2.0'),
            address='btc-address-123'
        )
        
        self.usd_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance=Decimal('10000.0'),
            address='usd-address-789'
        )
        
        # Create buy transactions
        self.transaction1 = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('1.0'),
            currency='BTC',
            native_amount=Decimal('40000.00'),  # Bought at $40,000
            native_currency='USD',
            status='completed',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            created_at=timezone.now() - timezone.timedelta(days=100)
        )
        
        self.transaction2 = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('1.0'),
            currency='BTC',
            native_amount=Decimal('45000.00'),  # Bought at $45,000
            native_currency='USD',
            status='completed',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            created_at=timezone.now() - timezone.timedelta(days=50)
        )
    
    def test_calculate_cost_basis_api(self):
        """Test cost basis calculation API"""
        response = self.client.post(
            reverse('api_calculate_cost_basis'),
            content_type='application/json',
            data=json.dumps({
                'crypto_code': 'BTC',
                'cost_basis_method': 'fifo',
                'tax_year': timezone.now().year
            })
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('results', data)
        self.assertIn('summary', data)
        # Should have 2 transactions in the results
        self.assertEqual(len(data['results']), 2)
        # Check summary calculation
        summary = data['summary']
        # Total cost basis should be 40000 + 45000 = 85000
        self.assertEqual(summary['total_cost_basis'], 85000.0)
