from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid

from trading_hub.models import (
    CryptoCurrency, Transaction, Wallet, TaxReport, TaxTransaction
)
from trading_hub.services.tax_calculator import TaxCalculator

class TaxCalculatorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Create cryptocurrency
        self.btc = CryptoCurrency.objects.create(
            code='BTC',
            name='Bitcoin',
            current_price_usd=Decimal('50000.00')
        )
        
        # Create wallets
        self.btc_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='BTC',
            balance=Decimal('1.5'),
            address='btc-address-123'
        )
        
        self.usd_wallet = Wallet.objects.create(
            user=self.user,
            currency_code='USD',
            balance=Decimal('25000.0'),
            address='usd-address-789'
        )
        
        # Create transactions for testing cost basis calculations
        
        # Buy 1.0 BTC at $30,000
        self.buy1 = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('1.0'),
            currency='BTC',
            native_amount=Decimal('30000.00'),
            native_currency='USD',
            status='completed',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            created_at=timezone.now() - timezone.timedelta(days=400)  # Over 1 year ago
        )
        
        # Buy 0.5 BTC at $25,000
        self.buy2 = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('0.5'),
            currency='BTC',
            native_amount=Decimal('25000.00'),
            native_currency='USD',
            status='completed',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            created_at=timezone.now() - timezone.timedelta(days=200)  # Under 1 year ago
        )
        
        # Sell 0.8 BTC at $45,000
        self.sell1 = Transaction.objects.create(
            user=self.user,
            transaction_type='sell',
            amount=Decimal('0.8'),
            currency='BTC',
            native_amount=Decimal('45000.00'),
            native_currency='USD',
            status='completed',
            from_wallet=self.btc_wallet,
            to_wallet=self.usd_wallet,
            created_at=timezone.now() - timezone.timedelta(days=100)
        )
        
        # Initialize tax calculator
        self.calculator = TaxCalculator(
            user=self.user,
            tax_year=timezone.now().year,
            cost_basis_method='fifo'
        )
    
    def test_calculate_cost_basis_fifo(self):
        """Test FIFO cost basis calculation"""
        # Calculate cost basis
        transactions = self.calculator.calculate_cost_basis('BTC')
        
        # Should have one transaction (the sell transaction)
        self.assertEqual(len(transactions), 1)
        tx_data = transactions[0]
        
        # Using FIFO, cost basis should be from the first buy: 0.8 BTC at $30,000 = $24,000
        self.assertEqual(tx_data['cost_basis'], Decimal('24000'))
        
        # Proceeds from selling 0.8 BTC at $45,000 = $36,000
        self.assertEqual(tx_data['proceeds'], Decimal('36000'))
        
        # Gain/loss = $36,000 - $24,000 = $12,000
        self.assertEqual(tx_data['gain_loss'], Decimal('12000'))
        
        # Should be long-term gain since first purchase was > 1 year ago
        self.assertTrue(tx_data['is_long_term'])
    
    def test_generate_tax_report(self):
        """Test tax report generation"""
        # Generate report
        tax_report = self.calculator.generate_tax_report(
            report_format='csv',
            include_unrealized=True
        )
        
        # Verify report was created
        self.assertIsNotNone(tax_report)
        self.assertEqual(tax_report.user, self.user)
        self.assertEqual(tax_report.tax_year, timezone.now().year)
        self.assertEqual(tax_report.report_format, 'csv')
        self.assertEqual(tax_report.include_unrealized_gains, True)
        
        # Should be in processing status initially
        self.assertEqual(tax_report.status, 'processing')
        
        # Check that TaxTransaction records were created
        tax_transactions = TaxTransaction.objects.filter(
            transaction__user=self.user,
            tax_year=timezone.now().year
        )
        self.assertEqual(tax_transactions.count(), 1)  # For the sell transaction
