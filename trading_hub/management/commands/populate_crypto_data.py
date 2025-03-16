import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from trading_hub.models import (
    CryptoCurrency,
    PriceHistory,
    WatchList,
    CoinbaseUser,
    Wallet
)


class Command(BaseCommand):
    help = 'Populates the database with sample cryptocurrency data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing cryptocurrency data before creating new data',
        )
        parser.add_argument(
            '--with-history',
            action='store_true',
            help='Generate price history data for charts',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Deleting existing cryptocurrency data...')
            CryptoCurrency.objects.all().delete()
            PriceHistory.objects.all().delete()

        # List of cryptocurrencies with realistic data
        crypto_data = [
            {
                'code': 'BTC',
                'name': 'Bitcoin',
                'current_price_usd': Decimal('67890.45'),
                'market_cap_usd': Decimal('1324578900000'),
                'volume_24h_usd': Decimal('42367891200'),
                'price_change_24h_percent': Decimal('2.45'),
            },
            {
                'code': 'ETH',
                'name': 'Ethereum',
                'current_price_usd': Decimal('3450.78'),
                'market_cap_usd': Decimal('415678900000'),
                'volume_24h_usd': Decimal('19876543210'),
                'price_change_24h_percent': Decimal('3.21'),
            },
            {
                'code': 'USDT',
                'name': 'Tether',
                'current_price_usd': Decimal('1.00'),
                'market_cap_usd': Decimal('89567890000'),
                'volume_24h_usd': Decimal('78912345000'),
                'price_change_24h_percent': Decimal('0.01'),
            },
            {
                'code': 'BNB',
                'name': 'Binance Coin',
                'current_price_usd': Decimal('567.89'),
                'market_cap_usd': Decimal('87654321000'),
                'volume_24h_usd': Decimal('2345678900'),
                'price_change_24h_percent': Decimal('-1.23'),
            },
            {
                'code': 'SOL',
                'name': 'Solana',
                'current_price_usd': Decimal('178.34'),
                'market_cap_usd': Decimal('65432198000'),
                'volume_24h_usd': Decimal('5678912300'),
                'price_change_24h_percent': Decimal('5.67'),
            },
            {
                'code': 'XRP',
                'name': 'XRP',
                'current_price_usd': Decimal('0.56'),
                'market_cap_usd': Decimal('28765432100'),
                'volume_24h_usd': Decimal('1987654320'),
                'price_change_24h_percent': Decimal('-2.34'),
            },
            {
                'code': 'USDC',
                'name': 'USD Coin',
                'current_price_usd': Decimal('1.00'),
                'market_cap_usd': Decimal('34567890000'),
                'volume_24h_usd': Decimal('3456789000'),
                'price_change_24h_percent': Decimal('0.00'),
            },
            {
                'code': 'ADA',
                'name': 'Cardano',
                'current_price_usd': Decimal('0.45'),
                'market_cap_usd': Decimal('15678900000'),
                'volume_24h_usd': Decimal('987654320'),
                'price_change_24h_percent': Decimal('1.78'),
            },
            {
                'code': 'DOGE',
                'name': 'Dogecoin',
                'current_price_usd': Decimal('0.092'),
                'market_cap_usd': Decimal('12456789000'),
                'volume_24h_usd': Decimal('976543210'),
                'price_change_24h_percent': Decimal('-0.98'),
            },
            {
                'code': 'SHIB',
                'name': 'Shiba Inu',
                'current_price_usd': Decimal('0.000023'),
                'market_cap_usd': Decimal('13567890000'),
                'volume_24h_usd': Decimal('654321980'),
                'price_change_24h_percent': Decimal('4.56'),
            },
        ]

        created_count = 0
        for data in crypto_data:
            crypto, created = CryptoCurrency.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'current_price_usd': data['current_price_usd'],
                    'market_cap_usd': data['market_cap_usd'],
                    'volume_24h_usd': data['volume_24h_usd'],
                    'price_change_24h_percent': data['price_change_24h_percent'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created {data["name"]} ({data["code"]})')
            else:
                self.stdout.write(f'Updated {data["name"]} ({data["code"]})')

            # Generate price history data if requested
            if options['with_history']:
                self.generate_price_history(crypto)

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} cryptocurrencies'))

        # Create default watchlist for existing users
        self.create_default_watchlists()

    def generate_price_history(self, crypto):
        """Generate price history data for a cryptocurrency"""
        periods = ['day', 'week', 'month', 'year', 'all']
        
        # Clear existing price history for this crypto
        PriceHistory.objects.filter(currency=crypto).delete()
        
        # For day period - generate hourly data for the last 24 hours
        base_price = float(crypto.current_price_usd)
        now = timezone.now()
        
        # Generate day data (24 hourly points)
        for hour in range(24):
            timestamp = now - timedelta(hours=23-hour)
            # Add some randomness to price (±3%)
            price_variation = random.uniform(-0.03, 0.03)
            price = base_price * (1 + price_variation * (hour/24))
            
            PriceHistory.objects.create(
                currency=crypto,
                price_usd=Decimal(str(price)),
                timestamp=timestamp,
                period='day'
            )
        
        # Generate week data (7 daily points)
        for day in range(7):
            timestamp = now - timedelta(days=6-day)
            price_variation = random.uniform(-0.08, 0.08)
            price = base_price * (1 + price_variation * (day/7))
            
            PriceHistory.objects.create(
                currency=crypto,
                price_usd=Decimal(str(price)),
                timestamp=timestamp,
                period='week'
            )
        
        # Generate month data (30 daily points)
        for day in range(30):
            timestamp = now - timedelta(days=29-day)
            price_variation = random.uniform(-0.15, 0.15)
            price = base_price * (1 + price_variation * (day/30))
            
            PriceHistory.objects.create(
                currency=crypto,
                price_usd=Decimal(str(price)),
                timestamp=timestamp,
                period='month'
            )
        
        # Generate year data (12 monthly points)
        for month in range(12):
            timestamp = now - timedelta(days=30*(11-month))
            price_variation = random.uniform(-0.4, 0.4)
            price = base_price * (1 + price_variation * (month/12))
            
            PriceHistory.objects.create(
                currency=crypto,
                price_usd=Decimal(str(price)),
                timestamp=timestamp,
                period='year'
            )
        
        self.stdout.write(f'  Generated price history for {crypto.name}')

    def create_default_watchlists(self):
        """Create default watchlists for all users"""
        users = User.objects.all()
        default_cryptos = CryptoCurrency.objects.all()[:5]  # First 5 cryptos
        
        for user in users:
            watchlist, created = WatchList.objects.get_or_create(
                user=user,
                name="My Watchlist"
            )
            
            if created or not watchlist.currencies.exists():
                for crypto in default_cryptos:
                    watchlist.currencies.add(crypto)
                self.stdout.write(f'Created default watchlist for {user.username}')