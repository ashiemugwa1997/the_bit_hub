from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string


class CoinbaseUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coinbase_profile')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_trades = models.PositiveIntegerField(default=0)
    successful_trades = models.PositiveIntegerField(default=0)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    identity_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Coinbase Profile"

    def calculate_rating(self):
        if self.total_trades > 0:
            success_rate = self.successful_trades / self.total_trades
            # Rating formula: 50% based on success rate (0-5 points) + base rating of 5
            new_rating = (success_rate * 5) + 5
            # Cap rating between 0-10
            self.rating = min(max(new_rating / 2, 0), 5)
            self.save()


# Create trader profile when a user is created
@receiver(post_save, sender=User)
def create_coinbase_user(sender, instance, created, **kwargs):
    if created:
        CoinbaseUser.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_coinbase_user(sender, instance, **kwargs):
    if hasattr(instance, 'coinbase_profile'):
        instance.coinbase_profile.save()


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    currency_code = models.CharField(max_length=10)  # BTC, ETH, USD, etc.
    name = models.CharField(max_length=50, default="My Wallet")
    balance = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    address = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s {self.currency_code} Wallet ({self.balance})"


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('send', 'Send'),
        ('receive', 'Receive'),
        ('convert', 'Convert'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=24, decimal_places=8)
    currency = models.CharField(max_length=10)  # BTC, ETH, etc.
    native_amount = models.DecimalField(max_digits=24, decimal_places=2)  # Amount in USD or local currency
    native_currency = models.CharField(max_length=5, default="USD")  # USD, EUR, etc.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    to_wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, related_name='incoming_transactions', null=True,
                                  blank=True)
    from_wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, related_name='outgoing_transactions', null=True,
                                    blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency}"

    def complete_transaction(self, successful=True):
        """Mark a transaction as complete and update user profile"""
        if successful:
            self.status = 'completed'

            # Update wallet balances
            if self.transaction_type == 'buy':
                self.to_wallet.balance += self.amount
                self.to_wallet.save()
            elif self.transaction_type == 'sell':
                self.from_wallet.balance -= self.amount
                self.from_wallet.save()
            elif self.transaction_type == 'send':
                self.from_wallet.balance -= self.amount
                self.from_wallet.save()
                if self.to_wallet:
                    self.to_wallet.balance += self.amount
                    self.to_wallet.save()
            elif self.transaction_type == 'receive':
                self.to_wallet.balance += self.amount
                self.to_wallet.save()
        else:
            self.status = 'failed'

        self.save()

        # Update trader profile
        profile = self.user.coinbase_profile
        profile.total_trades += 1
        if successful:
            profile.successful_trades += 1
        profile.calculate_rating()


class CryptoCurrency(models.Model):
    code = models.CharField(max_length=10, primary_key=True)  # BTC, ETH, etc.
    name = models.CharField(max_length=50)  # Bitcoin, Ethereum, etc.
    current_price_usd = models.DecimalField(max_digits=24, decimal_places=2)
    market_cap_usd = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    volume_24h_usd = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    price_change_24h_percent = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    icon = models.ImageField(upload_to='crypto_icons/', null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class WatchList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_lists')
    currencies = models.ManyToManyField(CryptoCurrency, related_name='in_watch_lists')
    name = models.CharField(max_length=50, default="My Watchlist")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s {self.name}"


# For Price Chart Data
class PriceHistory(models.Model):
    TIME_PERIODS = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year'),
        ('all', 'All Time'),
    )

    currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name='price_history')
    price_usd = models.DecimalField(max_digits=24, decimal_places=2)
    timestamp = models.DateTimeField()
    period = models.CharField(max_length=10, choices=TIME_PERIODS)

    def __str__(self):
        return f"{self.currency.code} price at {self.timestamp}"


# Payment Methods (like in Coinbase)
class PaymentMethod(models.Model):
    METHOD_TYPES = (
        ('bank', 'Bank Account'),
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    name = models.CharField(max_length=100)  # "Chase Bank Account", "Visa ending in 1234"
    method_type = models.CharField(max_length=10, choices=METHOD_TYPES)
    is_default = models.BooleanField(default=False)
    last_four = models.CharField(max_length=4, blank=True, null=True)  # Last 4 digits of card or account
    expires = models.DateField(null=True, blank=True)  # For cards
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s {self.name}"


class LimitOrder(models.Model):
    ORDER_STATUS = (
        ('open', 'Open'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    )
    
    SIDE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='limit_orders')
    cryptocurrency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    amount = models.DecimalField(max_digits=24, decimal_places=8)
    limit_price = models.DecimalField(max_digits=24, decimal_places=2)
    filled_amount = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='limit_order_source')
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='limit_order_destination', null=True, blank=True)
    
    def __str__(self):
        return f"{self.side.upper()} {self.amount} {self.cryptocurrency.code} @ {self.limit_price}"
    
    def can_execute(self):
        """Check if the order can be executed based on current market price"""
        current_price = self.cryptocurrency.current_price_usd
        if self.side == 'buy':
            return current_price <= self.limit_price
        else:  # sell
            return current_price >= self.limit_price
    
    def try_execute(self):
        """Attempt to execute the limit order if conditions are met"""
        if not self.can_execute() or self.status != 'open':
            return False
            
        try:
            if self.side == 'buy':
                usd_needed = (self.amount - self.filled_amount) * self.limit_price
                if self.from_wallet.balance >= usd_needed:
                    # Create transaction for the buy
                    transaction = Transaction.objects.create(
                        user=self.user,
                        transaction_type='buy',
                        amount=self.amount - self.filled_amount,
                        currency=self.cryptocurrency.code,
                        native_amount=usd_needed,
                        native_currency='USD',
                        from_wallet=self.from_wallet,
                        to_wallet=self.to_wallet,
                        description=f"Limit order buy executed at {self.limit_price}"
                    )
                    transaction.complete_transaction(successful=True)
                    self.filled_amount = self.amount
                    self.status = 'filled'
                    self.save()
                    return True
            else:  # sell
                crypto_available = self.from_wallet.balance
                if crypto_available >= (self.amount - self.filled_amount):
                    # Create transaction for the sell
                    usd_value = (self.amount - self.filled_amount) * self.limit_price
                    transaction = Transaction.objects.create(
                        user=self.user,
                        transaction_type='sell',
                        amount=self.amount - self.filled_amount,
                        currency=self.cryptocurrency.code,
                        native_amount=usd_value,
                        native_currency='USD',
                        from_wallet=self.from_wallet,
                        to_wallet=self.to_wallet,
                        description=f"Limit order sell executed at {self.limit_price}"
                    )
                    transaction.complete_transaction(successful=True)
                    self.filled_amount = self.amount
                    self.status = 'filled'
                    self.save()
                    return True
                    
        except Exception as e:
            print(f"Error executing limit order: {e}")
            return False
            
        return False
    
    def cancel(self):
        """Cancel an open limit order"""
        if self.status == 'open':
            self.status = 'cancelled'
            self.save()
            return True
        return False


class StopOrder(models.Model):
    ORDER_STATUS = (
        ('open', 'Open'),
        ('triggered', 'Triggered'),  # When stop price is reached but not yet executed
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    )
    
    SIDE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stop_orders')
    cryptocurrency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    amount = models.DecimalField(max_digits=24, decimal_places=8)
    stop_price = models.DecimalField(max_digits=24, decimal_places=2)  # Price that triggers the order
    limit_price = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)  # Optional limit price for stop-limit orders
    filled_amount = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    status = models.CharField(max_length=10, choices=ORDER_STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='stop_order_source')
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='stop_order_destination', null=True, blank=True)
    
    def __str__(self):
        order_type = "Stop-Limit" if self.limit_price else "Stop"
        return f"{order_type} {self.side.upper()} {self.amount} {self.cryptocurrency.code} @ {self.stop_price}"
    
    def should_trigger(self):
        """Check if the stop order should be triggered based on current market price"""
        current_price = self.cryptocurrency.current_price_usd
        if self.side == 'buy':
            # Buy stop triggers when price rises above stop price
            return current_price >= self.stop_price
        else:  # sell
            # Sell stop triggers when price falls below stop price
            return current_price <= self.stop_price
    
    def try_trigger(self):
        """Attempt to trigger the stop order if conditions are met"""
        if not self.should_trigger() or self.status != 'open':
            return False
            
        # Update status to triggered
        self.status = 'triggered'
        self.save()
        
        # If it's a stop-limit order, create a limit order
        if self.limit_price:
            limit_order = LimitOrder.objects.create(
                user=self.user,
                cryptocurrency=self.cryptocurrency,
                side=self.side,
                amount=self.amount,
                limit_price=self.limit_price,
                from_wallet=self.from_wallet,
                to_wallet=self.to_wallet,
                expires_at=self.expires_at
            )
            return True
            
        # Otherwise execute as market order
        try:
            if self.side == 'buy':
                usd_needed = self.amount * self.cryptocurrency.current_price_usd
                if self.from_wallet.balance >= usd_needed:
                    transaction = Transaction.objects.create(
                        user=self.user,
                        transaction_type='buy',
                        amount=self.amount,
                        currency=self.cryptocurrency.code,
                        native_amount=usd_needed,
                        native_currency='USD',
                        from_wallet=self.from_wallet,
                        to_wallet=self.to_wallet,
                        description=f"Stop order buy executed at market price {self.cryptocurrency.current_price_usd}"
                    )
                    transaction.complete_transaction(successful=True)
                    self.filled_amount = self.amount
                    self.status = 'filled'
                    self.save()
                    return True
            else:  # sell
                crypto_available = self.from_wallet.balance
                if crypto_available >= self.amount:
                    usd_value = self.amount * self.cryptocurrency.current_price_usd
                    transaction = Transaction.objects.create(
                        user=self.user,
                        transaction_type='sell',
                        amount=self.amount,
                        currency=self.cryptocurrency.code,
                        native_amount=usd_value,
                        native_currency='USD',
                        from_wallet=self.from_wallet,
                        to_wallet=self.to_wallet,
                        description=f"Stop order sell executed at market price {self.cryptocurrency.current_price_usd}"
                    )
                    transaction.complete_transaction(successful=True)
                    self.filled_amount = self.amount
                    self.status = 'filled'
                    self.save()
                    return True
                    
        except Exception as e:
            print(f"Error executing stop order: {e}")
            return False
            
        return False
    
    def cancel(self):
        """Cancel an open stop order"""
        if self.status == 'open':
            self.status = 'cancelled'
            self.save()
            return True
        return False


class RecurringOrder(models.Model):
    INTERVAL_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly')
    )
    
    ORDER_TYPE_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell')
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_orders')
    cryptocurrency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=4, choices=ORDER_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=24, decimal_places=8)  # Amount in crypto or USD
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='recurring_order_source')
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='recurring_order_destination', null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)  # Optional end date
    last_executed = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.order_type.upper()} {self.amount} {self.cryptocurrency.code} ({self.interval})"
        
    def calculate_next_execution(self):
        """Calculate the next execution date based on the interval and last execution"""
        now = timezone.now()
        base_date = self.last_executed if self.last_executed else self.start_date
        
        if self.interval == 'daily':
            next_date = base_date + timezone.timedelta(days=1)
        elif self.interval == 'weekly':
            next_date = base_date + timezone.timedelta(weeks=1)
        elif self.interval == 'biweekly':
            next_date = base_date + timezone.timedelta(weeks=2)
        elif self.interval == 'monthly':
            # Add one month (approximately handling month transitions)
            next_month = base_date.month + 1
            next_year = base_date.year + (next_month > 12)
            if next_month > 12:
                next_month -= 12
            next_date = base_date.replace(year=next_year, month=next_month)
        
        # If the calculated next date is in the past (could happen after pausing/resuming)
        # set it to the next occurrence from now
        if next_date < now:
            delta = now - base_date
            if self.interval == 'daily':
                days_passed = delta.days
                next_date = now + timezone.timedelta(days=1)
            elif self.interval == 'weekly':
                weeks_passed = delta.days // 7 + 1
                next_date = base_date + timezone.timedelta(weeks=weeks_passed)
            elif self.interval == 'biweekly':
                two_weeks_passed = delta.days // 14 + 1
                next_date = base_date + timezone.timedelta(weeks=2*two_weeks_passed)
            elif self.interval == 'monthly':
                months_passed = delta.days // 30 + 1
                next_month = base_date.month + months_passed
                next_year = base_date.year + (next_month > 12)
                if next_month > 12:
                    next_month = next_month % 12
                    if next_month == 0:
                        next_month = 12
                next_date = base_date.replace(year=next_year, month=next_month)
        
        return next_date
    
    def save(self, *args, **kwargs):
        """Override save to update next_execution date"""
        if not self.next_execution:
            self.next_execution = self.calculate_next_execution()
        super().save(*args, **kwargs)
    
    def pause(self):
        """Pause the recurring order"""
        if self.status == 'active':
            self.status = 'paused'
            self.save()
            return True
        return False
    
    def resume(self):
        """Resume the recurring order"""
        if self.status == 'paused':
            self.status = 'active'
            self.next_execution = self.calculate_next_execution()
            self.save()
            return True
        return False
    
    def cancel(self):
        """Cancel the recurring order"""
        if self.status in ['active', 'paused']:
            self.status = 'cancelled'
            self.save()
            return True
        return False
    
    def execute(self):
        """Execute this recurring order"""
        if self.status != 'active':
            return False
            
        try:
            current_price = self.cryptocurrency.current_price_usd
            
            if self.order_type == 'buy':
                if self.from_wallet.currency_code == 'USD':
                    usd_amount = self.amount
                    crypto_amount = usd_amount / current_price
                else:
                    # If amount is specified in crypto for a buy order
                    crypto_amount = self.amount
                    usd_amount = crypto_amount * current_price
                
                # Check if user has enough balance
                if self.from_wallet.balance < usd_amount:
                    print(f"Insufficient balance for recurring buy order {self.id}")
                    return False
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=self.user,
                    transaction_type='buy',
                    amount=crypto_amount,
                    currency=self.cryptocurrency.code,
                    native_amount=usd_amount,
                    native_currency='USD',
                    from_wallet=self.from_wallet,
                    to_wallet=self.to_wallet,
                    description=f"Recurring buy order executed at {current_price}"
                )
            else:  # sell
                if self.from_wallet.currency_code == self.cryptocurrency.code:
                    crypto_amount = self.amount
                    usd_amount = crypto_amount * current_price
                else:
                    # If amount is specified in USD for a sell order
                    usd_amount = self.amount
                    crypto_amount = usd_amount / current_price
                
                # Check if user has enough crypto
                if self.from_wallet.balance < crypto_amount:
                    print(f"Insufficient balance for recurring sell order {self.id}")
                    return False
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=self.user,
                    transaction_type='sell',
                    amount=crypto_amount,
                    currency=self.cryptocurrency.code,
                    native_amount=usd_amount,
                    native_currency='USD',
                    from_wallet=self.from_wallet,
                    to_wallet=self.to_wallet,
                    description=f"Recurring sell order executed at {current_price}"
                )
            
            # Complete the transaction
            transaction.complete_transaction(successful=True)
            
            # Update recurring order
            self.last_executed = timezone.now()
            self.next_execution = self.calculate_next_execution()
            
            # Check if we've reached the end date
            if self.end_date and self.next_execution > self.end_date:
                self.status = 'completed'
                
            self.save()
            return True
                
        except Exception as e:
            print(f"Error executing recurring order: {e}")
            return False


class TradingPair(models.Model):
    """Model to represent crypto-to-crypto trading pairs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name='base_trading_pairs')
    quote_currency = models.ForeignKey(CryptoCurrency, on_delete=models.CASCADE, related_name='quote_trading_pairs')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_price = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    price_change_24h_percent = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ('base_currency', 'quote_currency')
        verbose_name = 'Trading Pair'
        verbose_name_plural = 'Trading Pairs'
    
    def __str__(self):
        return f"{self.base_currency.code}/{self.quote_currency.code}"
    
    def get_pair_code(self):
        """Return the trading pair code (e.g., BTC/ETH)"""
        return f"{self.base_currency.code}/{self.quote_currency.code}"
    
    @property
    def inverse_rate(self):
        """Return the inverse exchange rate"""
        if self.last_price and self.last_price != 0:
            return Decimal('1') / self.last_price
        return None


class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.device_id})'


class KYC(models.Model):
    TIER_CHOICES = [
        ('tier_1', 'Tier 1'),
        ('tier_2', 'Tier 2'),
        ('tier_3', 'Tier 3'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=100)
    document_image = models.ImageField(upload_to='kyc_documents/')
    status = models.CharField(max_length=20, default='pending')
    rejection_reason = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    address_rejection_reason = models.TextField(null=True, blank=True)
    tier = models.CharField(max_length=20, default='tier_1')

    def __str__(self):
        return f'{self.user.username} - {self.document_type}'


class BankAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    routing_number = models.CharField(max_length=9)
    account_type = models.CharField(max_length=10, choices=[('checking', 'Checking'), ('savings', 'Savings')])
    account_holder_name = models.CharField(max_length=100, default="")  # Added from second definition
    ifsc_code = models.CharField(max_length=11, null=True, blank=True)  # Added from second definition
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Added from second definition

    def __str__(self):
        return f"{self.user.username}'s {self.bank_name} Account"


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)  # USD, EUR, etc.
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency}"


class PaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=[('card', 'Card'), ('bank', 'Bank'), ('crypto', 'Crypto')])
    provider = models.CharField(max_length=50)  # e.g., Visa, MasterCard, Bank Name, Crypto Wallet
    account_number = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.method_type} ({self.provider})"


class PriceAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    target_price = models.DecimalField(max_digits=20, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
    triggered = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.symbol} - {self.target_price}"


# Add the Asset model
class Asset(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=[
        ('crypto', 'Cryptocurrency'),
        ('stock', 'Stock'),
        ('forex', 'Foreign Exchange'),
        ('commodity', 'Commodity')
    ])
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"
    
    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'


class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    source = models.CharField(max_length=100)
    source_url = models.URLField()
    image_url = models.URLField(null=True, blank=True)
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.CharField(max_length=255, blank=True)
    related_cryptocurrencies = models.ManyToManyField(CryptoCurrency, blank=True)
    sentiment = models.CharField(
        max_length=10,
        choices=[('positive', 'Positive'), ('neutral', 'Neutral'), ('negative', 'Negative')],
        default='neutral'
    )
    featured = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'News Article'
        verbose_name_plural = 'News Articles'
        ordering = ['-published_at']


class APIKey(models.Model):
    """API keys for third-party developers to access BitHub API"""
    API_KEY_PERMISSIONS = (
        ('read', 'Read Only'),
        ('read_write', 'Read & Write'),
        ('admin', 'Admin Access')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100, help_text="A name to help you identify this API key")
    key = models.CharField(max_length=64, unique=True)
    secret = models.CharField(max_length=128)  # Will be hashed before storage
    permissions = models.CharField(max_length=20, choices=API_KEY_PERMISSIONS, default='read')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    allowed_ips = models.TextField(blank=True, null=True, 
                                  help_text="Comma-separated list of IP addresses allowed to use this key")
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def is_expired(self):
        """Check if the API key has expired"""
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False
    
    def has_valid_ip(self, request_ip):
        """Check if the request IP is allowed to use this key"""
        if not self.allowed_ips:
            return True
        
        allowed_ips = [ip.strip() for ip in self.allowed_ips.split(',')]
        return request_ip in allowed_ips
    
    def save(self, *args, **kwargs):
        """Override save to ensure the key is set"""
        if not self.key:
            self.key = self.generate_key()
            self.secret = self.generate_secret()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        """Generate a random API key"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    @staticmethod
    def generate_secret():
        """Generate a random API secret"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=64))


class APIRequestLog(models.Model):
    """Log of API requests for monitoring and rate limiting"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='api_requests')
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='requests')
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)  # GET, POST, PUT, DELETE, etc.
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    execution_time = models.FloatField(help_text="API request execution time in milliseconds")
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.endpoint} - {self.status_code}"
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['api_key', '-timestamp']),
            models.Index(fields=['endpoint', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]


class TaxReport(models.Model):
    """Model for storing generated tax reports"""
    TAX_YEAR_CHOICES = [(year, str(year)) for year in range(2020, timezone.now().year + 1)]
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    REPORT_FORMAT_CHOICES = (
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
        ('turbotax', 'TurboTax'),
        ('cointracker', 'CoinTracker'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_reports')
    tax_year = models.IntegerField(choices=TAX_YEAR_CHOICES, default=timezone.now().year)
    report_format = models.CharField(max_length=20, choices=REPORT_FORMAT_CHOICES, default='csv')
    include_unrealized_gains = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    report_file = models.FileField(upload_to='tax_reports/', null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.tax_year} Tax Report"
    
    def generate_report(self):
        """Start generating the tax report"""
        self.status = 'processing'
        self.save()
        
        try:
            # This would be implemented as a background task
            # For now, we'll just simulate it
            
            # Mark as completed
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            return True
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.save()
            return False

class TaxTransaction(models.Model):
    """Model for storing tax-relevant transaction details"""
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='tax_info')
    cost_basis = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    gain_loss = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    is_long_term = models.BooleanField(null=True, blank=True)  # True for holdings > 1 year
    tax_year = models.IntegerField()
    tax_category = models.CharField(max_length=50, blank=True, null=True)  # e.g., mining, airdrop, capital_gain
    
    def __str__(self):
        return f"Tax info for {self.transaction}"
