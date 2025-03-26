from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid
from datetime import datetime, timedelta

from trading_hub.models import (
    CoinbaseUser, Wallet, Transaction, CryptoCurrency,
    WatchList, LimitOrder, StopOrder, RecurringOrder,
    TradingPair, Device, KYC, BankAccount, PriceAlert,
    News, APIKey, TaxReport, TaxTransaction
)

class CoinbaseUserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.coinbase_profile = CoinbaseUser.objects.get(user=self.user)
    
    def test_coinbase_user_creation(self):
        """Test CoinbaseUser is created automatically when User is created"""
        self.assertTrue(isinstance(self.coinbase_profile, CoinbaseUser))
        self.assertEqual(self.coinbase_profile.rating, Decimal('5.00'))
        self.assertEqual(self.coinbase_profile.total_trades, 0)
        self.assertEqual(self.coinbase_profile.successful_trades, 0)
        self.assertEqual(self.coinbase_profile.__str__(), "testuser's Coinbase Profile")
    
    def test_rating_calculation(self):
        """Test CoinbaseUser rating calculation works correctly"""
        # Simulate some trades
        self.coinbase_profile.total_trades = 10
        self.coinbase_profile.successful_trades = 8
        self.coinbase_profile.calculate_rating()
        
        # 8/10 success rate = 0.8 * 5 + 5 = 9 / 2 = 4.5 rating
        self.assertEqual(self.coinbase_profile.rating, Decimal('4.50'))

class WalletModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.wallet = Wallet.objects.create(
            user=self.user,
            currency_code='BTC',
            name='Test Bitcoin Wallet',
            balance=Decimal('1.5'),
            address='test-address-123'
        )
    
    def test_wallet_creation(self):
        """Test Wallet creation works correctly"""
        self.assertTrue(isinstance(self.wallet, Wallet))
        self.assertEqual(self.wallet.currency_code, 'BTC')
        self.assertEqual(self.wallet.balance, Decimal('1.5'))
        self.assertEqual(self.wallet.__str__(), "testuser's BTC Wallet (1.5)")

class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Create wallets
        self.btc_wallet = Wallet.objects.create(
            user=self.user, 
            currency_code='BTC', 
            balance=Decimal('1.0'),
            address='btc-wallet-1'
        )
        
        self.usd_wallet = Wallet.objects.create(
            user=self.user, 
            currency_code='USD', 
            balance=Decimal('1000.0'),
            address='usd-wallet-1'
        )
        
        # Create transaction
        self.transaction = Transaction.objects.create(
            user=self.user,
            transaction_type='buy',
            amount=Decimal('0.1'),
            currency='BTC',
            native_amount=Decimal('5000.00'),
            native_currency='USD',
            status='pending',
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet,
            description='Test purchase'
        )
    
    def test_transaction_creation(self):
        """Test Transaction creation works correctly"""
        self.assertTrue(isinstance(self.transaction, Transaction))
        self.assertEqual(self.transaction.transaction_type, 'buy')
        self.assertEqual(self.transaction.amount, Decimal('0.1'))
        self.assertEqual(self.transaction.__str__(), "buy - 0.1 BTC")
    
    def test_transaction_completion(self):
        """Test completing a transaction updates balances correctly"""
        # Initial balances
        initial_btc = self.btc_wallet.balance
        initial_usd = self.usd_wallet.balance
        
        # Complete the transaction
        self.transaction.complete_transaction(successful=True)
        
        # Refresh wallets from DB
        self.btc_wallet.refresh_from_db()
        self.usd_wallet.refresh_from_db()
        
        # Verify balances updated
        self.assertEqual(self.btc_wallet.balance, initial_btc + Decimal('0.1'))
        self.assertEqual(self.usd_wallet.balance, initial_usd - Decimal('5000.00'))
        
        # Verify transaction status
        self.assertEqual(self.transaction.status, 'completed')

class CryptoCurrencyModelTest(TestCase):
    def setUp(self):
        self.btc = CryptoCurrency.objects.create(
            code='BTC',
            name='Bitcoin',
            current_price_usd=Decimal('50000.00'),
            market_cap_usd=Decimal('1000000000000.00'),
            volume_24h_usd=Decimal('50000000000.00'),
            price_change_24h_percent=Decimal('2.5')
        )
    
    def test_cryptocurrency_creation(self):
        """Test CryptoCurrency creation works correctly"""
        self.assertTrue(isinstance(self.btc, CryptoCurrency))
        self.assertEqual(self.btc.code, 'BTC')
        self.assertEqual(self.btc.current_price_usd, Decimal('50000.00'))
        self.assertEqual(self.btc.__str__(), "Bitcoin (BTC)")

class LimitOrderModelTest(TestCase):
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
            balance=Decimal('1.0'),
            address='btc-wallet-1'
        )
        
        self.usd_wallet = Wallet.objects.create(
            user=self.user, 
            currency_code='USD', 
            balance=Decimal('60000.0'),
            address='usd-wallet-1'
        )
        
        # Create buy limit order (lower than current price)
        self.buy_limit_order = LimitOrder.objects.create(
            user=self.user,
            cryptocurrency=self.btc,
            side='buy',
            amount=Decimal('1.0'),
            limit_price=Decimal('48000.00'),
            from_wallet=self.usd_wallet,
            to_wallet=self.btc_wallet
        )
        
        # Create sell limit order (higher than current price)
        self.sell_limit_order = LimitOrder.objects.create(
            user=self.user,
            cryptocurrency=self.btc,
            side='sell',
            amount=Decimal('0.5'),
            limit_price=Decimal('52000.00'),
            from_wallet=self.btc_wallet,
            to_wallet=self.usd_wallet
        )
    
    def test_limit_order_creation(self):
        """Test LimitOrder creation works correctly"""
        self.assertTrue(isinstance(self.buy_limit_order, LimitOrder))
        self.assertEqual(self.buy_limit_order.side, 'buy')
        self.assertEqual(self.buy_limit_order.limit_price, Decimal('48000.00'))
        self.assertEqual(self.buy_limit_order.__str__(), "BUY 1.0 BTC @ 48000.00")
    
    def test_can_execute_logic(self):
        """Test the can_execute method correctly determines when orders can be executed"""
        # Current price is 50000, so neither order should execute yet
        self.assertFalse(self.buy_limit_order.can_execute())
        self.assertFalse(self.sell_limit_order.can_execute())
        
        # Change prices to make orders executable
        self.btc.current_price_usd = Decimal('47000.00')
        self.btc.save()
        self.assertTrue(self.buy_limit_order.can_execute())
        self.assertFalse(self.sell_limit_order.can_execute())
        
        self.btc.current_price_usd = Decimal('53000.00')
        self.btc.save()
        self.assertFalse(self.buy_limit_order.can_execute())
        self.assertTrue(self.sell_limit_order.can_execute())

# More test classes would follow for other models...

class TaxReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.tax_report = TaxReport.objects.create(
            user=self.user,
            tax_year=2023,
            report_format='csv',
            include_unrealized_gains=False
        )
    
    def test_tax_report_creation(self):
        """Test TaxReport creation works correctly"""
        self.assertTrue(isinstance(self.tax_report, TaxReport))
        self.assertEqual(self.tax_report.tax_year, 2023)
        self.assertEqual(self.tax_report.status, 'pending')
        self.assertEqual(self.tax_report.__str__(), "testuser's 2023 Tax Report")
