from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import json
import uuid
import random
import string
from datetime import datetime, timedelta
from .models import (
    CryptoCurrency, Wallet, Transaction, LimitOrder, StopOrder, 
    RecurringOrder, TradingPair, Device, KYC, BankAccount, News,
    PriceAlert, APIKey, TaxReport, TaxTransaction  # Added TaxReport and TaxTransaction import here
)
from .forms import KYCForm, AddressForm, BankAccountForm, PriceAlertForm, TaxReportForm  # Added TaxReportForm import here
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView  # Added DetailView import here
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods  # Added require_http_methods import here
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from .services.tax_calculator import TaxCalculator  # Added TaxCalculator import here
import os  # Added os import here

# Import the API form if the module exists
try:
    from .api.forms import APIKeyForm
except (ImportError, ModuleNotFoundError):
    # Create a simple placeholder form if API module isn't available
    class APIKeyForm(forms.ModelForm):
        class Meta:
            model = APIKey
            fields = ['name', 'permissions', 'allowed_ips']

@login_required
def dashboard(request):
    # Get user's wallets
    wallets = Wallet.objects.filter(user=request.user)
    
    # Calculate total portfolio value
    portfolio_value = Decimal('0.00')
    wallet_data = []
    
    for wallet in wallets:
        if wallet.currency_code == 'USD':
            value = wallet.balance
        else:
            try:
                crypto = CryptoCurrency.objects.get(code=wallet.currency_code)
                value = wallet.balance * crypto.current_price_usd
            except CryptoCurrency.DoesNotExist:
                value = Decimal('0.00')
        
        wallet_data.append({
            'code': wallet.currency_code,
            'balance': wallet.balance,
            'value': value,
        })
        portfolio_value += value
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get trending cryptocurrencies
    trending_cryptos = CryptoCurrency.objects.all().order_by('-price_change_24h_percent')[:5]
    
    return render(request, 'trading_hub/dashboard.html', {
        'wallet_data': wallet_data,
        'portfolio_value': portfolio_value,
        'recent_transactions': recent_transactions,
        'trending_cryptos': trending_cryptos,
    })

@login_required
def asset_list(request):
    user_wallets = Wallet.objects.filter(user=request.user)
    
    # Create a dictionary of user's crypto balances
    user_balances = {}
    for wallet in user_wallets:
        user_balances[wallet.currency_code] = wallet
    
    # Get all cryptocurrencies
    all_cryptos = CryptoCurrency.objects.all().order_by('name')
    
    # Check if user has balance or not
    crypto_data = []
    for crypto in all_cryptos:
        if crypto.code in user_balances:
            balance = user_balances[crypto.code].balance
            balance_usd = balance * crypto.current_price_usd
            has_balance = True
        else:
            balance = Decimal('0')
            balance_usd = Decimal('0')
            has_balance = False
        
        crypto_data.append({
            'crypto': crypto,
            'balance': balance,
            'balance_usd': balance_usd,
            'has_balance': has_balance,
        })
    
    return render(request, 'trading_hub/asset_list.html', {
        'crypto_data': crypto_data,
    })

@login_required
def crypto_detail(request, code):
    # Get the cryptocurrency
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Get user's wallet for this crypto
    try:
        wallet = Wallet.objects.get(user=request.user, currency_code=crypto.code)
    except Wallet.DoesNotExist:
        wallet = None
        
    # Get recent transactions for this crypto
    transactions = Transaction.objects.filter(
        user=request.user,
        currency=crypto.code
    ).order_by('-created_at')[:5]
        
    return render(request, 'trading_hub/crypto_detail.html', {
        'crypto': crypto,
        'wallet': wallet,
        'transactions': transactions,
    })

@login_required
def create_trade(request, code):
    """Common function for buy and sell operations"""
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Get or create user's crypto wallet
    crypto_wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        currency_code=crypto.code,
        defaults={
            'name': f"My {crypto.name} Wallet",
            'balance': Decimal('0'),
            'address': str(uuid.uuid4())  # Generate a random address
        }
    )
    
    # Get user's USD wallet
    try:
        usd_wallet = Wallet.objects.get(user=request.user, currency_code='USD')
    except Wallet.DoesNotExist:
        # Create a USD wallet if it doesn't exist
        usd_wallet = Wallet.objects.create(
            user=request.user,
            currency_code='USD',
            name="My USD Wallet",
            balance=Decimal('10000.00'),  # Start with $10,000 for demo
            address=str(uuid.uuid4())
        )
    
    is_buy = 'buy' in request.path
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
            
            if is_buy:
                # Calculate USD cost (with a small spread)
                usd_amount = amount * crypto.current_price_usd * Decimal('1.005')  # 0.5% spread
                
                if usd_wallet.balance < usd_amount:
                    messages.error(request, "Insufficient USD balance.")
                    return render(request, 'trading_hub/create_trade.html', {
                        'crypto': crypto, 
                        'wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'is_buy': is_buy,
                    })
                
                # Create the transaction
                with transaction.atomic():
                    tx = Transaction.objects.create(
                        user=request.user,
                        transaction_type='buy',
                        amount=amount,
                        currency=crypto.code,
                        native_amount=usd_amount,
                        native_currency='USD',
                        status='completed',
                        description=f"Market buy of {amount} {crypto.code}",
                        from_wallet=usd_wallet,
                        to_wallet=crypto_wallet
                    )
                    
                    # Update wallet balances
                    usd_wallet.balance -= usd_amount
                    usd_wallet.save()
                    
                    crypto_wallet.balance += amount
                    crypto_wallet.save()
                
                messages.success(request, f"Successfully bought {amount} {crypto.code}")
                return redirect('crypto_detail', code=crypto.code)
            else:
                # Sell crypto
                if crypto_wallet.balance < amount:
                    messages.error(request, f"Insufficient {crypto.code} balance.")
                    return render(request, 'trading_hub/create_trade.html', {
                        'crypto': crypto, 
                        'wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'is_buy': is_buy,
                    })
                    
                # Calculate USD amount (with a small spread)
                usd_amount = amount * crypto.current_price_usd * Decimal('0.995')  # 0.5% spread
                
                # Create the transaction
                with transaction.atomic():
                    tx = Transaction.objects.create(
                        user=request.user,
                        transaction_type='sell',
                        amount=amount,
                        currency=crypto.code,
                        native_amount=usd_amount,
                        native_currency='USD',
                        status='completed',
                        description=f"Market sell of {amount} {crypto.code}",
                        from_wallet=crypto_wallet,
                        to_wallet=usd_wallet
                    )
                    
                    # Update wallet balances
                    crypto_wallet.balance -= amount
                    crypto_wallet.save()
                    
                    usd_wallet.balance += usd_amount
                    usd_wallet.save()
                
                messages.success(request, f"Successfully sold {amount} {crypto.code}")
                return redirect('crypto_detail', code=crypto.code)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Invalid amount: {str(e)}")
    
    return render(request, 'trading_hub/create_trade.html', {
        'crypto': crypto,
        'wallet': crypto_wallet,
        'usd_wallet': usd_wallet,
        'is_buy': is_buy,
    })

@login_required
def buy_crypto(request, code):
    return create_trade(request, code)

@login_required
def sell_crypto(request, code):
    return create_trade(request, code)

@login_required
def send_crypto(request, code):
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Get user's wallet for this crypto
    try:
        wallet = Wallet.objects.get(user=request.user, currency_code=crypto.code)
    except Wallet.DoesNotExist:
        messages.error(request, f"You don't have a {crypto.code} wallet.")
        return redirect('crypto_detail', code=crypto.code)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            address = request.POST.get('address', '').strip()
            
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
                
            if not address:
                raise ValueError("Recipient address is required")
                
            if wallet.balance < amount:
                messages.error(request, f"Insufficient {crypto.code} balance.")
                return render(request, 'trading_hub/send_crypto.html', {
                    'crypto': crypto, 
                    'wallet': wallet,
                })
            
            # For demo purposes, just create a transaction
            with transaction.atomic():
                tx = Transaction.objects.create(
                    user=request.user,
                    transaction_type='send',
                    amount=amount,
                    currency=crypto.code,
                    native_amount=amount * crypto.current_price_usd,
                    native_currency='USD',
                    status='completed',
                    description=f"Sent {amount} {crypto.code} to {address[:10]}...",
                    from_wallet=wallet,
                )
                
                # Update wallet balance
                wallet.balance -= amount
                wallet.save()
            
            messages.success(request, f"Successfully sent {amount} {crypto.code}")
            return redirect('crypto_detail', code=crypto.code)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'trading_hub/send_crypto.html', {
        'crypto': crypto,
        'wallet': wallet,
    })

@login_required
def create_limit_order(request, code):
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Default order side (buy/sell)
    default_side = request.GET.get('side', 'buy')
    
    # Get user's wallets
    try:
        crypto_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code=crypto.code,
            defaults={
                'name': f"My {crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )
        
        usd_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code='USD',
            defaults={
                'name': "My USD Wallet",
                'balance': Decimal('10000.00'),
                'address': str(uuid.uuid4())
            }
        )
    except Exception as e:
        messages.error(request, f"Error accessing wallets: {str(e)}")
        return redirect('crypto_detail', code=crypto.code)
    
    if request.method == 'POST':
        try:
            side = request.POST.get('side', default_side)
            amount = Decimal(request.POST.get('amount', '0'))
            price = Decimal(request.POST.get('price', '0'))
            
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
                
            if price <= 0:
                raise ValueError("Price must be greater than zero")
            
            # Check if user has sufficient balance
            if side == 'buy':
                required_usd = amount * price
                
                if usd_wallet.balance < required_usd:
                    messages.error(request, "Insufficient USD balance.")
                    return render(request, 'trading_hub/create_limit_order.html', {
                        'crypto': crypto,
                        'crypto_wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'default_side': side,
                        'current_price': crypto.current_price_usd,
                    })
                    
                from_wallet = usd_wallet
                to_wallet = crypto_wallet
            else:
                if crypto_wallet.balance < amount:
                    messages.error(request, f"Insufficient {crypto.code} balance.")
                    return render(request, 'trading_hub/create_limit_order.html', {
                        'crypto': crypto,
                        'crypto_wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'default_side': side,
                        'current_price': crypto.current_price_usd,
                    })
                    
                from_wallet = crypto_wallet
                to_wallet = usd_wallet
            
            # Create limit order
            order = LimitOrder.objects.create(
                user=request.user,
                cryptocurrency=crypto,
                side=side,
                amount=amount,
                limit_price=price,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                # Set expiration date if needed
                expires_at=timezone.now() + timezone.timedelta(days=30)
            )
            
            messages.success(request, f"Limit order created successfully.")
            return redirect('limit_order_detail', order_id=order.id)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error creating order: {str(e)}")
    
    return render(request, 'trading_hub/create_limit_order.html', {
        'crypto': crypto,
        'crypto_wallet': crypto_wallet,
        'usd_wallet': usd_wallet,
        'default_side': default_side,
        'current_price': crypto.current_price_usd,
    })

@login_required
def limit_order_list(request):
    orders = LimitOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trading_hub/limit_order_list.html', {'orders': orders})

@login_required
def limit_order_detail(request, order_id):
    order = get_object_or_404(LimitOrder, id=order_id, user=request.user)
    
    if request.method == 'POST' and 'cancel' in request.POST:
        order.cancel()
        messages.success(request, "Order cancelled successfully.")
        return redirect('limit_order_list')
    
    return render(request, 'trading_hub/limit_order_detail.html', {'order': order})

@login_required
def create_stop_order(request, code):
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Default values from URL parameters
    default_side = request.GET.get('side', 'buy')
    stop_limit = request.GET.get('stop_limit', 'false') == 'true'
    
    # Get user's wallets
    try:
        crypto_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code=crypto.code,
            defaults={
                'name': f"My {crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )
        
        usd_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code='USD',
            defaults={
                'name': "My USD Wallet",
                'balance': Decimal('10000.00'),
                'address': str(uuid.uuid4())
            }
        )
    except Exception as e:
        messages.error(request, f"Error accessing wallets: {str(e)}")
        return redirect('crypto_detail', code=crypto.code)
    
    if request.method == 'POST':
        try:
            side = request.POST.get('side', default_side)
            amount = Decimal(request.POST.get('amount', '0'))
            stop_price = Decimal(request.POST.get('stop_price', '0'))
            limit_price = None
            
            if 'limit_price' in request.POST and request.POST.get('limit_price'):
                limit_price = Decimal(request.POST.get('limit_price', '0'))
            
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
                
            if stop_price <= 0:
                raise ValueError("Stop price must be greater than zero")
                
            if limit_price is not None and limit_price <= 0:
                raise ValueError("Limit price must be greater than zero")
            
            # Check if user has sufficient balance
            if side == 'buy':
                # For buy stop orders, we need USD
                required_usd = amount * (limit_price or stop_price)
                
                if usd_wallet.balance < required_usd:
                    messages.error(request, "Insufficient USD balance.")
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'crypto_wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'default_side': side,
                        'current_price': crypto.current_price_usd,
                        'stop_limit': stop_limit,
                    })
                    
                from_wallet = usd_wallet
                to_wallet = crypto_wallet
            else:
                # For sell stop orders, we need crypto
                if crypto_wallet.balance < amount:
                    messages.error(request, f"Insufficient {crypto.code} balance.")
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'crypto_wallet': crypto_wallet,
                        'usd_wallet': usd_wallet,
                        'default_side': side,
                        'current_price': crypto.current_price_usd,
                        'stop_limit': stop_limit,
                    })
                    
                from_wallet = crypto_wallet
                to_wallet = usd_wallet
            
            # Create stop order
            order = StopOrder.objects.create(
                user=request.user,
                cryptocurrency=crypto,
                side=side,
                amount=amount,
                stop_price=stop_price,
                limit_price=limit_price,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                # Set expiration date if needed
                expires_at=timezone.now() + timezone.timedelta(days=30)
            )
            
            messages.success(request, f"Stop order created successfully.")
            return redirect('stop_order_detail', order_id=order.id)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error creating order: {str(e)}")
    
    return render(request, 'trading_hub/create_stop_order.html', {
        'crypto': crypto,
        'crypto_wallet': crypto_wallet,
        'usd_wallet': usd_wallet,
        'default_side': default_side,
        'current_price': crypto.current_price_usd,
        'stop_limit': stop_limit,
    })

@login_required
def stop_order_list(request):
    orders = StopOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trading_hub/stop_order_list.html', {'orders': orders})

@login_required
def stop_order_detail(request, order_id):
    order = get_object_or_404(StopOrder, id=order_id, user=request.user)
    
    if request.method == 'POST' and 'cancel' in request.POST:
        order.cancel()
        messages.success(request, "Order cancelled successfully.")
        return redirect('stop_order_list')
    
    return render(request, 'trading_hub/stop_order_detail.html', {'order': order})

@login_required
def create_recurring_order(request, code):
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('asset_list')
    
    # Default values from URL parameters
    default_side = request.GET.get('side', 'buy')
    
    # Get user's wallets
    try:
        crypto_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code=crypto.code,
            defaults={
                'name': f"My {crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )
        
        usd_wallet, _ = Wallet.objects.get_or_create(
            user=request.user, 
            currency_code='USD',
            defaults={
                'name': "My USD Wallet",
                'balance': Decimal('10000.00'),
                'address': str(uuid.uuid4())
            }
        )
    except Exception as e:
        messages.error(request, f"Error accessing wallets: {str(e)}")
        return redirect('crypto_detail', code=crypto.code)
    
    if request.method == 'POST':
        try:
            order_type = request.POST.get('order_type', default_side)
            amount = Decimal(request.POST.get('amount', '0'))
            interval = request.POST.get('interval')
            
            # Optional end date
            end_date_str = request.POST.get('end_date', '').strip()
            end_date = None
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
                
            if not interval:
                raise ValueError("Please select an interval")
            
            # Determine source and destination wallets
            if order_type == 'buy':
                from_wallet = usd_wallet
                to_wallet = crypto_wallet
            else:  # sell
                from_wallet = crypto_wallet
                to_wallet = usd_wallet
            
            # Create recurring order
            start_date = timezone.now()
            order = RecurringOrder.objects.create(
                user=request.user,
                cryptocurrency=crypto,
                order_type=order_type,
                amount=amount,
                interval=interval,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                start_date=start_date,
                end_date=end_date,
                next_execution=start_date
            )
            
            # Calculate the next execution date
            order.next_execution = order.calculate_next_execution()
            order.save()
            
            messages.success(request, f"Recurring order created successfully.")
            return redirect('recurring_order_detail', order_id=order.id)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error creating order: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")
    
    return render(request, 'trading_hub/create_recurring_order.html', {
        'crypto': crypto,
        'crypto_wallet': crypto_wallet,
        'usd_wallet': usd_wallet,
        'default_side': default_side,
        'current_price': crypto.current_price_usd,
        'intervals': RecurringOrder.INTERVAL_CHOICES,
    })

@login_required
def recurring_order_list(request):
    orders = RecurringOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trading_hub/recurring_order_list.html', {'orders': orders})

@login_required
def recurring_order_detail(request, order_id):
    order = get_object_or_404(RecurringOrder, id=order_id, user=request.user)
    
    if request.method == 'POST':
        if 'cancel' in request.POST:
            order.cancel()
            messages.success(request, "Recurring order cancelled.")
            return redirect('recurring_order_list')
        elif 'pause' in request.POST:
            order.pause()
            messages.success(request, "Recurring order paused.")
        elif 'resume' in request.POST:
            order.resume()
            messages.success(request, "Recurring order resumed.")
    
    return render(request, 'trading_hub/recurring_order_detail.html', {'order': order})

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trading_hub/transaction_history.html', {'transactions': transactions})

@login_required
def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    return render(request, 'trading_hub/transaction_detail.html', {'transaction': transaction})

@login_required
def wallet_list(request):
    """View to display all user's wallets"""
    wallets = Wallet.objects.filter(user=request.user)
    
    wallet_data = []
    total_value_usd = Decimal('0.00')
    
    for wallet in wallets:
        if wallet.currency_code == 'USD':
            value_usd = wallet.balance
        else:
            try:
                crypto = CryptoCurrency.objects.get(code=wallet.currency_code)
                value_usd = wallet.balance * crypto.current_price_usd
            except CryptoCurrency.DoesNotExist:
                value_usd = Decimal('0.00')
        
        wallet_data.append({
            'wallet': wallet,
            'value_usd': value_usd
        })
        total_value_usd += value_usd
    
    return render(request, 'trading_hub/wallet_list.html', {
        'wallet_data': wallet_data,
        'total_value_usd': total_value_usd
    })

@login_required
def create_crypto_trade(request, base_code, quote_code):
    try:
        base_crypto = CryptoCurrency.objects.get(code=base_code)
        quote_crypto = CryptoCurrency.objects.get(code=quote_code)
        trading_pair = TradingPair.objects.get(base_currency=base_crypto, quote_currency=quote_crypto)
    except (CryptoCurrency.DoesNotExist, TradingPair.DoesNotExist):
        messages.error(request, "Invalid trading pair")
        return redirect('asset_list')

    # Get user's wallets
    try:
        base_wallet, _ = Wallet.objects.get_or_create(
            user=request.user,
            currency_code=base_code,
            defaults={
                'name': f"My {base_crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )
        quote_wallet, _ = Wallet.objects.get_or_create(
            user=request.user,
            currency_code=quote_code,
            defaults={
                'name': f"My {quote_crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )
    except Exception as e:
        messages.error(request, f"Error accessing wallets: {str(e)}")
        return redirect('asset_list')

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")

            # Calculate the conversion rate using both cryptocurrencies' USD prices
            conversion_rate = quote_crypto.current_price_usd / base_crypto.current_price_usd
            quote_amount = amount * conversion_rate

            # Validate sufficient balance
            if base_wallet.balance < amount:
                raise ValueError(f"Insufficient {base_code} balance")

            # Create and execute the transaction
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='convert',
                from_wallet=base_wallet,
                to_wallet=quote_wallet,
                from_amount=amount,
                to_amount=quote_amount,
                price_usd=base_crypto.current_price_usd,
                status='completed'
            )

            # Update wallet balances
            base_wallet.balance -= amount
            quote_wallet.balance += quote_amount
            base_wallet.save()
            quote_wallet.save()

            messages.success(request, f"Successfully converted {amount} {base_code} to {quote_amount:.8f} {quote_code}")
            return redirect('transaction_detail', transaction_id=transaction.id)

        except (ValueError, TypeError) as e:
            messages.error(request, f"Error creating trade: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'trading_hub/create_crypto_trade.html', {
        'base_crypto': base_crypto,
        'quote_crypto': quote_crypto,
        'trading_pair': trading_pair,
        'base_wallet': base_wallet,
        'quote_wallet': quote_wallet,
    })

@login_required
def conversion_pairs(request):
    """View to show available conversion pairs"""
    cryptocurrencies = CryptoCurrency.objects.all().order_by('code')
    user_wallets = Wallet.objects.filter(user=request.user)
    
    wallet_balances = {
        wallet.currency_code: wallet.balance 
        for wallet in user_wallets
    }
    
    context = {
        'cryptocurrencies': cryptocurrencies,
        'wallet_balances': wallet_balances
    }
    return render(request, 'trading_hub/convert/pairs.html', context)

@login_required
def convert_crypto(request, from_code, to_code):
    """Handle cryptocurrency conversion"""
    try:
        from_crypto = CryptoCurrency.objects.get(code=from_code.upper())
        to_crypto = CryptoCurrency.objects.get(code=to_code.upper())
        
        # Get or create user's wallets
        from_wallet = Wallet.objects.get_or_create(
            user=request.user,
            currency_code=from_code.upper(),
            defaults={
                'name': f"My {from_crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )[0]
        
        to_wallet = Wallet.objects.get_or_create(
            user=request.user,
            currency_code=to_code.upper(),
            defaults={
                'name': f"My {to_crypto.name} Wallet",
                'balance': Decimal('0'),
                'address': str(uuid.uuid4())
            }
        )[0]
        
        if request.method == 'POST':
            amount = Decimal(request.POST.get('amount', '0'))
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
                
            if from_wallet.balance < amount:
                messages.error(request, f"Insufficient {from_code} balance")
                return redirect('convert_crypto', from_code=from_code, to_code=to_code)
                
            # Calculate conversion rate using USD prices
            conversion_rate = to_crypto.current_price_usd / from_crypto.current_price_usd
            converted_amount = amount * conversion_rate
            
            # Create and execute the conversion transaction
            with transaction.atomic():
                tx = Transaction.objects.create(
                    user=request.user,
                    transaction_type='convert',
                    amount=amount,
                    currency=from_code,
                    native_amount=amount * from_crypto.current_price_usd,
                    native_currency='USD',
                    status='completed',
                    description=f"Converted {amount} {from_code} to {converted_amount} {to_code}",
                    from_wallet=from_wallet,
                    to_wallet=to_wallet
                )
                
                # Update wallet balances
                from_wallet.balance -= amount
                from_wallet.save()
                
                to_wallet.balance += converted_amount
                to_wallet.save()
                
            messages.success(request, f"Successfully converted {amount} {from_code} to {converted_amount:.8f} {to_code}")
            return redirect('dashboard')
                
    except (CryptoCurrency.DoesNotExist, ValueError, TypeError) as e:
        messages.error(request, str(e))
        return redirect('conversion_pairs')
    
    context = {
        'from_crypto': from_crypto,
        'to_crypto': to_crypto,
        'from_wallet': from_wallet,
        'to_wallet': to_wallet,
        'conversion_rate': to_crypto.current_price_usd / from_crypto.current_price_usd
    }
    return render(request, 'trading_hub/convert/convert.html', context)

@login_required
def get_conversion_rate(request, from_code, to_code):
    """API endpoint to get current conversion rate"""
    try:
        from_crypto = CryptoCurrency.objects.get(code=from_code.upper())
        to_crypto = CryptoCurrency.objects.get(code=to_code.upper())
        
        conversion_rate = to_crypto.current_price_usd / from_crypto.current_price_usd
        
        return JsonResponse({
            'from': from_code,
            'to': to_code,
            'rate': float(conversion_rate),
            'timestamp': timezone.now().isoformat()
        })
    except CryptoCurrency.DoesNotExist:
        return JsonResponse({'error': 'Invalid cryptocurrency code'}, status=400)

def profile(request):
    return render(request, 'trading_hub/profile.html')

def payment_methods(request):
    return render(request, 'trading_hub/payment_methods.html')

def order_book(request):
    limit_orders = LimitOrder.objects.all()
    stop_orders = StopOrder.objects.all()
    context = {
        'limit_orders': limit_orders,
        'stop_orders': stop_orders,
    }
    return render(request, 'trading_hub/order_book.html', context)

def depth_chart_data(request):
    limit_orders = LimitOrder.objects.all().order_by('limit_price')
    stop_orders = StopOrder.objects.all().order_by('stop_price')

    bids = []
    asks = []
    labels = []

    for order in limit_orders:
        if order.side == 'buy':
            bids.append(order.amount)
            labels.append(order.limit_price)
        else:
            asks.append(order.amount)
            labels.append(order.limit_price)

    for order in stop_orders:
        if order.side == 'buy':
            bids.append(order.amount)
            labels.append(order.stop_price)
        else:
            asks.append(order.amount)
            labels.append(order.stop_price)

    data = {
        'labels': labels,
        'bids': bids,
        'asks': asks,
    }

    return JsonResponse(data)

@login_required
def device_list(request):
    devices = Device.objects.filter(user=request.user)
    return render(request, 'trading_hub/device_list.html', {'devices': devices})

@login_required
def device_register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        device_id = request.POST.get('device_id')
        if name and device_id:
            Device.objects.create(user=request.user, name=name, device_id=device_id)
            messages.success(request, 'Device registered successfully.')
            return redirect('device_list')
        else:
            messages.error(request, 'Please provide both name and device ID.')
    return render(request, 'trading_hub/device_register.html')

@login_required
def device_remove(request, device_id):
    try:
        device = Device.objects.get(user=request.user, device_id=device_id)
        device.delete()
        messages.success(request, 'Device removed successfully.')
    except Device.DoesNotExist:
        messages.error(request, 'Device not found.')
    return redirect('device_list')

@login_required
def kyc_submit(request):
    if request.method == 'POST':
        form = KYCForm(request.POST, request.FILES)
        if form.is_valid():
            kyc = form.save(commit=False)
            kyc.user = request.user
            kyc.save()
            messages.success(request, 'KYC submitted successfully.')
            return redirect('kyc_status')
    else:
        form = KYCForm()
    return render(request, 'trading_hub/kyc_submit.html', {'form': form})

@login_required
def kyc_status(request):
    try:
        kyc = KYC.objects.get(user=request.user)
    except KYC.DoesNotExist:
        kyc = None
    return render(request, 'trading_hub/kyc_status.html', {'kyc': kyc})

@staff_member_required
def kyc_list(request):
    pending_kyc = KYC.objects.filter(status='pending')
    return render(request, 'trading_hub/kyc_list.html', {'pending_kyc': pending_kyc})

@staff_member_required
def kyc_verify(request, kyc_id):
    kyc = KYC.objects.get(id=kyc_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            kyc.status = 'verified'
            kyc.verified_at = timezone.now()
            kyc.save()
            messages.success(request, 'KYC verified successfully.')
        elif action == 'reject':
            kyc.status = 'rejected'
            kyc.rejection_reason = request.POST.get('rejection_reason')
            kyc.save()
            messages.success(request, 'KYC rejected.')
        return redirect('kyc_list')
    return render(request, 'trading_hub/kyc_verify.html', {'kyc': kyc})

@login_required
def address_submit(request):
    try:
        kyc = KYC.objects.get(user=request.user)
    except KYC.DoesNotExist:
        kyc = None
    if request.method == 'POST':
        kyc.address_line1 = request.POST.get('address_line1')
        kyc.address_line2 = request.POST.get('address_line2')
        kyc.city = request.POST.get('city')
        kyc.state = request.POST.get('state')
        kyc.postal_code = request.POST.get('postal_code')
        kyc.country = request.POST.get('country')
        kyc.save()
        messages.success(request, 'Address submitted successfully.')
        return redirect('kyc_status')
    return render(request, 'trading_hub/address_submit.html', {'kyc': kyc})

@staff_member_required
def address_verify(request, kyc_id):
    kyc = KYC.objects.get(id=kyc_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            kyc.status = 'address_verified'
            kyc.verified_at = timezone.now()
            kyc.save()
            messages.success(request, 'Address verified successfully.')
        elif action == 'reject':
            kyc.status = 'address_rejected'
            kyc.address_rejection_reason = request.POST.get('address_rejection_reason')
            kyc.save()
            messages.success(request, 'Address rejected.')
        return redirect('kyc_list')
    return render(request, 'trading_hub/address_verify.html', {'kyc': kyc})

@login_required
def submit_kyc(request):
    if request.method == 'POST':
        form = KYCForm(request.POST, request.FILES)
        if form.is_valid():
            kyc = form.save(commit=False)
            kyc.user = request.user
            kyc.save()
            return redirect('kyc_status')
    else:
        form = KYCForm()
    return render(request, 'trading_hub/kyc_submit.html', {'form': form})

@login_required
def kyc_status(request):
    kyc = KYC.objects.filter(user=request.user).first()
    return render(request, 'trading_hub/kyc_status.html', {'kyc': kyc})

@staff_member_required
def verify_kyc(request, kyc_id):
    kyc = KYC.objects.get(id=kyc_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            kyc.status = 'verified'
            kyc.verified_at = timezone.now()
            kyc.save()
        elif action == 'reject':
            kyc.status = 'rejected'
            kyc.rejection_reason = request.POST.get('rejection_reason')
            kyc.save()
        return redirect('kyc_list')
    return render(request, 'trading_hub/kyc_verify.html', {'kyc': kyc})

@staff_member_required
def kyc_list(request):
    kycs = KYC.objects.all()
    return render(request, 'trading_hub/kyc_list.html', {'kycs': kycs})

@login_required
def submit_address(request):
    kyc = KYC.objects.filter(user=request.user).first()
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            kyc.address_line1 = form.cleaned_data['address_line1']
            kyc.address_line2 = form.cleaned_data['address_line2']
            kyc.city = form.cleaned_data['city']
            kyc.state = form.cleaned_data['state']
            kyc.postal_code = form.cleaned_data['postal_code']
            kyc.country = form.cleaned_data['country']
            kyc.save()
            return redirect('kyc_status')
    else:
        form = AddressForm()
    return render(request, 'trading_hub/address_submit.html', {'form': form})

@staff_member_required
def verify_address(request, kyc_id):
    kyc = KYC.objects.get(id=kyc_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            kyc.status = 'address_verified'
            kyc.verified_at = timezone.now()
            kyc.save()
        elif action == 'reject':
            kyc.status = 'address_rejected'
            kyc.address_rejection_reason = request.POST.get('address_rejection_reason')
            kyc.save()
        return redirect('kyc_list')
    return render(request, 'trading_hub/address_verify.html', {'kyc': kyc})

@staff_member_required
def verify_tier(request, kyc_id):
    kyc = KYC.objects.get(id=kyc_id)
    if request.method == 'POST':
        tier = request.POST.get('tier')
        kyc.tier = tier
        kyc.save()
        return redirect('kyc_list')
    return render(request, 'trading_hub/kyc_verify.html', {'kyc': kyc})

@login_required
def verify_tier_1(request):
    if request.method == 'POST':
        # Handle tier 1 verification
        pass
    return render(request, 'trading_hub/verify_tier_1.html')

@login_required
def verify_tier_2(request):
    if request.method == 'POST':
        # Handle tier 2 verification
        pass
    return render(request, 'trading_hub/verify_tier_2.html')

@login_required
def verify_tier_3(request):
    if request.method == 'POST':
        # Handle tier 3 verification
        pass
    return render(request, 'trading_hub/verify_tier_3.html')

@login_required
def add_bank_account(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank_account = form.save(commit=False)
            bank_account.user = request.user
            bank_account.save()
            messages.success(request, 'Bank account added successfully.')
            return redirect('bank_account_list')
    else:
        form = BankAccountForm()
    return render(request, 'trading_hub/add_bank_account.html', {'form': form})

@login_required
def update_bank_account(request, pk):
    bank_account = get_object_or_404(BankAccount, pk=pk)
    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bank account updated successfully.')
            return redirect('bank_account_list')
    else:
        form = BankAccountForm(instance=bank_account)
    return render(request, 'trading_hub/update_bank_account.html', {'form': form})

@login_required
def delete_bank_account(request, pk):
    bank_account = get_object_or_404(BankAccount, pk=pk)
    if request.method == 'POST':
        bank_account.delete()
        messages.success(request, 'Bank account deleted successfully.')
        return redirect('bank_account_list')
    return render(request, 'trading_hub/delete_bank_account.html', {'bank_account': bank_account})

@login_required
def bank_account_list(request):
    bank_accounts = BankAccount.objects.filter(user=request.user)
    return render(request, 'trading_hub/bank_account_list.html', {'bank_accounts': bank_accounts})

@login_required
def initiate_wire_transfer(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        bank_account_id = request.POST.get('bank_account_id')
        
        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('initiate_wire_transfer')
        
        try:
            bank_account = BankAccount.objects.get(id=bank_account_id, user=request.user)
        except BankAccount.DoesNotExist:
            messages.error(request, 'Invalid bank account.')
            return redirect('initiate_wire_transfer')
        
        # Create the wire transfer transaction
        with transaction.atomic():
            tx = Transaction.objects.create(
                user=request.user,
                transaction_type='wire_transfer',
                amount=amount,
                currency='USD',
                status='pending',
                description=f'Wire transfer of {amount} USD to {bank_account.bank_name}',
                from_wallet=None,
                to_wallet=None
            )
            
            # Here you would integrate with the actual wire transfer service
            
            messages.success(request, f'Successfully initiated wire transfer of {amount} USD to {bank_account.bank_name}.')
            return redirect('dashboard')
    
    bank_accounts = BankAccount.objects.filter(user=request.user)
    return render(request, 'trading_hub/initiate_wire_transfer.html', {'bank_accounts': bank_accounts})

class PriceAlertListView(ListView):
    model = PriceAlert
    template_name = 'trading_hub/price_alert_list.html'

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)

class PriceAlertCreateView(CreateView):
    model = PriceAlert
    form_class = PriceAlertForm
    template_name = 'trading_hub/price_alert_form.html'
    success_url = reverse_lazy('price_alert_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class PriceAlertUpdateView(UpdateView):
    model = PriceAlert
    form_class = PriceAlertForm
    template_name = 'trading_hub/price_alert_form.html'
    success_url = reverse_lazy('price_alert_list')

class PriceAlertDeleteView(DeleteView):
    model = PriceAlert
    template_name = 'trading_hub/price_alert_confirm_delete.html'
    success_url = reverse_lazy('price_alert_list')

from django.http import JsonResponse
from .models import Asset, Transaction


def mobile_dashboard(request):
    # Implement the logic for the mobile dashboard
    data = {
        'message': 'Mobile dashboard data'
    }
    return JsonResponse(data)


def mobile_asset_list(request):
    # Implement the logic for listing assets
    assets = Asset.objects.all()
    data = {
        'assets': list(assets.values())
    }
    return JsonResponse(data)


def mobile_crypto_detail(request, code):
    # Implement the logic for crypto detail
    try:
        asset = Asset.objects.get(code=code)
        data = {
            'asset': {
                'code': asset.code,
                'name': asset.name,
                'price': asset.price,
                'description': asset.description
            }
        }
    except Asset.DoesNotExist:
        data = {
            'error': 'Asset not found'
        }
    return JsonResponse(data)


def mobile_transaction_history(request):
    # Implement the logic for transaction history
    transactions = Transaction.objects.filter(user=request.user)
    data = {
        'transactions': list(transactions.values())
    }
    return JsonResponse(data)

@csrf_exempt
@require_POST
def register_user(request):
    try:
        data = json.loads(request.body)
        username = data['username']
        password = data['password']
        email = data['email']

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)

        user = User.objects.create_user(username=username, password=password, email=email)
        user.save()

        return JsonResponse({'message': 'User registered successfully'}, status=201)
    except KeyError:
        return JsonResponse({'error': 'Invalid data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def register_user(request):
    """View for handling user registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optional: Add email field
            email = request.POST.get('email')
            if email:
                user.email = email
                user.save()
            
            # Log the user in after registration
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            
            messages.success(request, "Your account has been successfully created!")
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

from django.http import JsonResponse

def mobile_profile(request):
    """View function for mobile profile page"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Get the user's profile information
    user = request.user
    try:
        profile = user.coinbase_profile
        data = {
            'username': user.username,
            'email': user.email,
            'rating': float(profile.rating) if profile.rating else 0.0,
            'total_trades': profile.total_trades,
            'successful_trades': profile.successful_trades,
            'phone_verified': profile.phone_verified,
            'identity_verified': profile.identity_verified,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def education_home(request):
    """View for the main education/learning resources page"""
    return render(request, 'trading_hub/education/home.html')

def trading_basics(request):
    """Educational content about trading basics"""
    return render(request, 'trading_hub/education/trading_basics.html')

def crypto_fundamentals(request):
    """Educational content about cryptocurrency fundamentals"""
    return render(request, 'trading_hub/education/crypto_fundamentals.html')

def technical_analysis(request):
    """Educational content about technical analysis"""
    return render(request, 'trading_hub/education/technical_analysis.html')

def risk_management(request):
    """Educational content about risk management"""
    return render(request, 'trading_hub/education/risk_management.html')

def platform_guide(request):
    """Guide for using BitHub platform features"""
    return render(request, 'trading_hub/education/platform_guide.html')

@login_required
def news_feed(request):
    """View for the main news feed page"""
    news_articles = News.objects.all().order_by('-published_at')[:20]
    featured_articles = News.objects.filter(featured=True).order_by('-published_at')[:5]
    
    context = {
        'news_articles': news_articles,
        'featured_articles': featured_articles,
    }
    return render(request, 'trading_hub/news/feed.html', context)

@login_required
def news_detail(request, news_id):
    """View for a single news article"""
    article = get_object_or_404(News, id=news_id)
    related_news = News.objects.filter(
        Q(categories__icontains=article.categories) | 
        Q(related_cryptocurrencies__in=article.related_cryptocurrencies.all())
    ).exclude(id=article.id).distinct()[:5]
    
    context = {
        'article': article,
        'related_news': related_news,
    }
    return render(request, 'trading_hub/news/detail.html', context)

@login_required
def news_category(request, category):
    """View for news filtered by category"""
    news_articles = News.objects.filter(categories__icontains=category).order_by('-published_at')
    
    context = {
        'news_articles': news_articles,
        'category': category,
    }
    return render(request, 'trading_hub/news/category.html', context)

@login_required
def news_by_crypto(request, code):
    """View for news related to a specific cryptocurrency"""
    try:
        crypto = CryptoCurrency.objects.get(code=code.upper())
        news_articles = News.objects.filter(related_cryptocurrencies=crypto).order_by('-published_at')
        
        context = {
            'news_articles': news_articles,
            'crypto': crypto,
        }
        return render(request, 'trading_hub/news/by_crypto.html', context)
    except CryptoCurrency.DoesNotExist:
        messages.error(request, f"Cryptocurrency {code} not found.")
        return redirect('news_feed')

@login_required
def market_insights(request):
    """View for showing market insights and analysis"""
    # Get news with analysis or insights
    articles = News.objects.filter(
        Q(categories__icontains='analysis') | 
        Q(categories__icontains='insight') |
        Q(categories__icontains='opinion')
    ).order_by('-published_at')[:10]
    
    context = {
        'articles': articles,
    }
    return render(request, 'trading_hub/news/insights.html', context)

@login_required
def api_key_list(request):
    """View to list user's API keys"""
    api_keys = APIKey.objects.filter(user=request.user)
    
    context = {
        'api_keys': api_keys,
    }
    return render(request, 'trading_hub/api/key_list.html', context)

class APIKeyCreateView(LoginRequiredMixin, CreateView):
    """View to create a new API key"""
    model = APIKey
    form_class = APIKeyForm
    template_name = 'trading_hub/api/key_form.html'
    success_url = reverse_lazy('api_key_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # Show the API key and secret to the user only once
        self.request.session['new_api_key'] = {
            'key': self.object.key,
            'secret': self.object.secret
        }
        
        return response

class APIKeyDetailView(LoginRequiredMixin, DetailView):
    """View to see API key details"""
    model = APIKey
    template_name = 'trading_hub/api/key_detail.html'
    context_object_name = 'api_key'
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)

class APIKeyUpdateView(LoginRequiredMixin, UpdateView):
    """View to update an API key"""
    model = APIKey
    form_class = APIKeyForm
    template_name = 'trading_hub/api/key_form.html'
    success_url = reverse_lazy('api_key_list')
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Remove expiry_days field for updates
        if 'expiry_days' in form.fields:
            del form.fields['expiry_days']
        return form

class APIKeyDeleteView(LoginRequiredMixin, DeleteView):
    """View to delete an API key"""
    model = APIKey
    template_name = 'trading_hub/api/key_confirm_delete.html'
    success_url = reverse_lazy('api_key_list')
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)

@login_required
def api_key_regenerate_secret(request, pk):
    """View to regenerate API key secret"""
    try:
        api_key = APIKey.objects.get(pk=pk, user=request.user)
    except APIKey.DoesNotExist:
        messages.error(request, "API key not found.")
        return redirect('api_key_list')
    
    if request.method == 'POST':
        # Generate new secret
        api_key.secret = APIKey.generate_secret()
        api_key.save()
        
        # Store new secret to display once
        request.session['new_api_key'] = {
            'key': api_key.key,
            'secret': api_key.secret
        }
        
        messages.success(request, "API key secret regenerated successfully.")
        return redirect('api_key_detail', pk=api_key.pk)
    
    return render(request, 'trading_hub/api/key_regenerate_secret.html', {'api_key': api_key})

@login_required
def api_documentation(request):
    """View for API documentation"""
    return render(request, 'trading_hub/api/documentation.html')

@login_required
def tax_center(request):
    """Main view for tax reporting center"""
    # Get existing tax reports for this user
    reports = TaxReport.objects.filter(user=request.user).order_by('-tax_year', '-created_at')
    
    # Get tax years with transactions
    tax_years = Transaction.objects.filter(
        user=request.user
    ).dates('created_at', 'year')
    
    # Convert QuerySet to list of years
    years = [date.year for date in tax_years]
    
    # Current year should also be an option
    current_year = timezone.now().year
    if current_year not in years:
        years.append(current_year)
    
    # Sort years in descending order
    years.sort(reverse=True)
    
    context = {
        'reports': reports,
        'tax_years': years
    }
    
    return render(request, 'trading_hub/tax/center.html', context)

@login_required
def create_tax_report(request):
    """View for creating a new tax report"""
    if request.method == 'POST':
        form = TaxReportForm(request.POST)
        if form.is_valid():
            tax_year = form.cleaned_data['tax_year']
            cost_basis_method = form.cleaned_data['cost_basis_method']
            report_format = form.cleaned_data['report_format']
            include_unrealized = form.cleaned_data['include_unrealized_gains']
            
            # Initialize tax calculator
            calculator = TaxCalculator(
                user=request.user,
                tax_year=tax_year,
                cost_basis_method=cost_basis_method
            )
            
            # Generate the report
            tax_report = calculator.generate_tax_report(
                report_format=report_format,
                include_unrealized=include_unrealized
            )
            
            messages.success(request, "Tax report generated successfully.")
            return redirect('tax_report_detail', report_id=tax_report.id)
    else:
        form = TaxReportForm()
    
    context = {
        'form': form
    }
    
    return render(request, 'trading_hub/tax/create_report.html', context)

@login_required
def tax_report_detail(request, report_id):
    """View for tax report details"""
    tax_report = get_object_or_404(TaxReport, id=report_id, user=request.user)
    
    # Get tax transactions for this report
    tax_transactions = TaxTransaction.objects.filter(
        transaction__user=request.user,
        tax_year=tax_report.tax_year
    ).select_related('transaction').order_by('-transaction__created_at')
    
    # Calculate summary numbers
    short_term_gains = sum(tx.gain_loss for tx in tax_transactions if not tx.is_long_term)
    long_term_gains = sum(tx.gain_loss for tx in tax_transactions if tx.is_long_term)
    total_gains = short_term_gains + long_term_gains
    
    context = {
        'report': tax_report,
        'tax_transactions': tax_transactions,
        'short_term_gains': short_term_gains,
        'long_term_gains': long_term_gains,
        'total_gains': total_gains
    }
    
    return render(request, 'trading_hub/tax/report_detail.html', context)

@login_required
@require_http_methods(["GET"])
def download_tax_report(request, report_id):
    """View for downloading a tax report file"""
    tax_report = get_object_or_404(TaxReport, id=report_id, user=request.user)
    
    if not tax_report.report_file:
        messages.error(request, "Report file not found.")
        return redirect('tax_report_detail', report_id=tax_report.id)
    
    # Get the file path
    file_path = tax_report.report_file.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        messages.error(request, "Report file not found on server.")
        return redirect('tax_report_detail', report_id=tax_report.id)
    
    # Determine content type based on file extension
    content_type = 'text/csv'  # Default for CSV
    if file_path.endswith('.pdf'):
        content_type = 'application/pdf'
        
    # Return the file as a download response
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response

@login_required
def annual_tax_summary(request, year=None):
    """View for annual tax summary"""
    # If year is not specified, use current year
    if year is None:
        year = timezone.now().year
    
    # Initialize tax calculator
    calculator = TaxCalculator(
        user=request.user,
        tax_year=year
    )
    
    # Get annual summary
    summary = calculator.get_annual_summary()
    
    # Get unrealized gains
    unrealized_gains = calculator.calculate_unrealized_gains()
    
    context = {
        'year': year,
        'summary': summary,
        'unrealized_gains': unrealized_gains
    }
    
    return render(request, 'trading_hub/tax/annual_summary.html', context)

@login_required
def cost_basis_calculator(request):
    """Interactive cost basis calculator"""
    cryptocurrencies = CryptoCurrency.objects.all()
    
    context = {
        'cryptocurrencies': cryptocurrencies
    }
    
    return render(request, 'trading_hub/tax/cost_basis_calculator.html', context)

@login_required
def api_calculate_cost_basis(request):
    """API endpoint for cost basis calculator"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        crypto_code = data.get('crypto_code')
        cost_basis_method = data.get('cost_basis_method', 'fifo')
        tax_year = data.get('tax_year', timezone.now().year)
        
        if not crypto_code:
            return JsonResponse({'error': 'Cryptocurrency code is required'}, status=400)
        
        # Initialize tax calculator
        calculator = TaxCalculator(
            user=request.user,
            tax_year=tax_year,
            cost_basis_method=cost_basis_method
        )
        
        # Calculate cost basis
        transactions = calculator.calculate_cost_basis(crypto_code)
        
        # Format results for API response
        results = []
        for tx_data in transactions:
            tx = tx_data['transaction']
            results.append({
                'date': tx.created_at.isoformat(),
                'type': tx.transaction_type,
                'amount': float(tx.amount),
                'proceeds': float(tx_data['proceeds']),
                'cost_basis': float(tx_data['cost_basis']),
                'gain_loss': float(tx_data['gain_loss']),
                'is_long_term': tx_data['is_long_term']
            })
        
        return JsonResponse({
            'results': results,
            'summary': {
                'total_proceeds': float(sum(tx['proceeds'] for tx in results)),
                'total_cost_basis': float(sum(tx['cost_basis'] for tx in results)),
                'total_gain_loss': float(sum(tx['gain_loss'] for tx in results))
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
