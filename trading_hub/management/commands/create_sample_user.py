import random
import uuid
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from trading_hub.models import (
    CryptoCurrency, 
    CoinbaseUser,
    Wallet,
    Transaction,
    PaymentMethod
)


class Command(BaseCommand):
    help = 'Create a sample user with wallets and transactions for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='demouser',
            help='Username for the sample user',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='password123',
            help='Password for the sample user',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample user data before creating new data',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']

        if options['clear']:
            # Delete existing user and related data
            try:
                user = User.objects.get(username=username)
                self.stdout.write(f'Deleting existing user {username} and related data...')
                user.delete()
            except User.DoesNotExist:
                pass

        # Create user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created sample user: {username}'))
        else:
            self.stdout.write(f'User {username} already exists')
            # Ensure the profile exists
            if not hasattr(user, 'coinbase_profile'):
                CoinbaseUser.objects.create(user=user)
            
        # Make sure cryptocurrencies exist
        cryptos = CryptoCurrency.objects.all()
        if not cryptos.exists():
            self.stdout.write(
                'No cryptocurrencies found. Please run populate_crypto_data command first.'
            )
            return
            
        # Set up payment methods
        self.create_payment_methods(user)
        
        # Create wallets and transactions
        self.create_wallets_and_transactions(user)
        
        self.stdout.write(self.style.SUCCESS('Sample user setup complete!'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
            
    def create_payment_methods(self, user):
        """Create sample payment methods for the user"""
        # Clear existing methods
        PaymentMethod.objects.filter(user=user).delete()
        
        # Create a bank account
        PaymentMethod.objects.create(
            user=user,
            name="Chase Bank Account",
            method_type="bank",
            last_four="4567",
            is_default=True
        )
        
        # Create a credit card
        PaymentMethod.objects.create(
            user=user,
            name="Visa Credit Card",
            method_type="card",
            last_four="9876",
            expires=timezone.now().date() + timedelta(days=365)
        )
        
        self.stdout.write('Created payment methods')
        
    def create_wallets_and_transactions(self, user):
        """Create sample wallets and transactions for the user"""
        # Get a few cryptocurrencies to work with
        cryptos = list(CryptoCurrency.objects.all()[:5])
        
        # Create USD wallet with balance
        usd_wallet, _ = Wallet.objects.get_or_create(
            user=user,
            currency_code='USD',
            defaults={
                'name': 'US Dollar Wallet',
                'balance': Decimal('10000.00'),  # $10,000 balance
                'address': f'usd_{uuid.uuid4().hex[:16]}',
            }
        )
        usd_wallet.balance = Decimal('10000.00')
        usd_wallet.save()
        
        for crypto in cryptos:
            # Create or update wallet for this crypto
            wallet, created = Wallet.objects.get_or_create(
                user=user,
                currency_code=crypto.code,
                defaults={
                    'name': f'My {crypto.name} Wallet',
                    'balance': Decimal('0'),
                    'address': f'cb_{uuid.uuid4().hex[:16]}',
                }
            )
            
            # Reset balance for existing wallets if needed
            if not created:
                wallet.balance = Decimal('0')
                wallet.save()
                
            # Create sample buy transactions over the past month
            self.create_buy_transactions(user, crypto, wallet)
            
            # Create some sell transactions if the wallet has enough balance
            if wallet.balance > Decimal('0'):
                self.create_sell_transactions(user, crypto, wallet, usd_wallet)
                
            # Generate a few send/receive transactions
            self.create_send_receive_transactions(user, crypto, wallet)
                
            self.stdout.write(f'Created wallet and transactions for {crypto.code}')
            
    def create_buy_transactions(self, user, crypto, wallet):
        """Create sample buy transactions for the given crypto"""
        # Generate 3-5 random buy transactions over the past month
        num_transactions = random.randint(3, 5)
        
        for i in range(num_transactions):
            # Random amount to buy (in USD)
            usd_amount = Decimal(str(random.uniform(100, 1000)))
            
            # Calculate crypto amount based on current price
            crypto_amount = usd_amount / crypto.current_price_usd
            
            # Random date in the past month
            days_ago = random.randint(1, 30)
            transaction_date = timezone.now() - timedelta(days=days_ago)
            
            # Create transaction
            transaction = Transaction.objects.create(
                user=user,
                transaction_type='buy',
                amount=crypto_amount,
                currency=crypto.code,
                native_amount=usd_amount,
                native_currency='USD',
                to_wallet=wallet,
                description=f"Bought {crypto_amount} {crypto.code}",
                created_at=transaction_date,
                status='completed',
            )
            
            # Update wallet balance
            wallet.balance += crypto_amount
            wallet.save()
            
    def create_sell_transactions(self, user, crypto, wallet, usd_wallet):
        """Create sample sell transactions for the given crypto"""
        # Only sell up to 40% of the balance
        available_to_sell = wallet.balance * Decimal('0.4')
        
        if available_to_sell < Decimal('0.0001'):
            return
            
        # Generate 1-3 random sell transactions
        num_transactions = random.randint(1, 3)
        
        for i in range(num_transactions):
            # Random amount to sell (up to 40% of available)
            crypto_amount = Decimal(str(random.uniform(
                float(available_to_sell / Decimal(num_transactions) * Decimal('0.5')),
                float(available_to_sell / Decimal(num_transactions))
            )))
            
            if crypto_amount < Decimal('0.0001'):
                continue
                
            # Calculate USD amount
            usd_amount = crypto_amount * crypto.current_price_usd
            
            # Random date in the past month (but after buys)
            days_ago = random.randint(1, 20)
            transaction_date = timezone.now() - timedelta(days=days_ago)
            
            # Create transaction
            transaction = Transaction.objects.create(
                user=user,
                transaction_type='sell',
                amount=crypto_amount,
                currency=crypto.code,
                native_amount=usd_amount,
                native_currency='USD',
                from_wallet=wallet,
                to_wallet=usd_wallet,
                description=f"Sold {crypto_amount} {crypto.code}",
                created_at=transaction_date,
                status='completed',
            )
            
            # Update wallet balances
            wallet.balance -= crypto_amount
            wallet.save()
            
            usd_wallet.balance += usd_amount
            usd_wallet.save()
            
    def create_send_receive_transactions(self, user, crypto, wallet):
        """Create sample send/receive transactions"""
        # Only if we have some balance
        if wallet.balance < Decimal('0.001'):
            return
            
        # Maybe create a small send transaction
        if random.random() > 0.5:
            send_amount = wallet.balance * Decimal(str(random.uniform(0.05, 0.1)))
            
            if send_amount >= Decimal('0.0001'):
                days_ago = random.randint(1, 15)
                transaction_date = timezone.now() - timedelta(days=days_ago)
                
                # Random destination address
                dest_address = f"extern_{uuid.uuid4().hex}"
                
                Transaction.objects.create(
                    user=user,
                    transaction_type='send',
                    amount=send_amount,
                    currency=crypto.code,
                    native_amount=send_amount * crypto.current_price_usd,
                    native_currency='USD',
                    from_wallet=wallet,
                    description=f"Sent {send_amount} {crypto.code} to {dest_address[:10]}...",
                    created_at=transaction_date,
                    status='completed',
                )
                
                # Update wallet balance
                wallet.balance -= send_amount
                wallet.save()
        
        # Maybe create a small receive transaction
        if random.random() > 0.5:
            receive_amount = wallet.balance * Decimal(str(random.uniform(0.05, 0.2)))
            
            if receive_amount >= Decimal('0.0001'):
                days_ago = random.randint(1, 10)
                transaction_date = timezone.now() - timedelta(days=days_ago)
                
                # Random source address
                source_address = f"extern_{uuid.uuid4().hex}"
                
                Transaction.objects.create(
                    user=user,
                    transaction_type='receive',
                    amount=receive_amount,
                    currency=crypto.code,
                    native_amount=receive_amount * crypto.current_price_usd,
                    native_currency='USD',
                    to_wallet=wallet,
                    description=f"Received {receive_amount} {crypto.code} from {source_address[:10]}...",
                    created_at=transaction_date,
                    status='completed',
                )
                
                # Update wallet balance
                wallet.balance += receive_amount
                wallet.save()