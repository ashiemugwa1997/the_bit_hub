from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import CoinbaseUser, Wallet

# The User post_save signals have already been defined in models.py,
# so we don't need to repeat them here. This file exists to be imported
# by the app's ready() method.

# You can add any additional signals you need below:

@receiver(post_save, sender=User)
def create_default_wallets(sender, instance, created, **kwargs):
    """Create default wallets for new users"""
    if created:
        # Create a default USD wallet for new users
        Wallet.objects.create(
            user=instance,
            currency_code='USD',
            name='USD Wallet',
            balance=1000.00,  # Starting with $1000 for testing
            address=f'usd-wallet-{instance.id}'
        )

        # Add more default wallets as needed
        default_cryptocurrencies = [
            ('BTC', 'Bitcoin Wallet'),
            ('ETH', 'Ethereum Wallet'),
        ]
        
        for code, name in default_cryptocurrencies:
            Wallet.objects.create(
                user=instance,
                currency_code=code,
                name=name,
                balance=0.0,
                address=f'{code.lower()}-wallet-{instance.id}'
            )
