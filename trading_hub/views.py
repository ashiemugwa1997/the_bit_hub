from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import json
import uuid
from datetime import datetime, timedelta
from .models import CryptoCurrency, Wallet, Transaction, LimitOrder, StopOrder, RecurringOrder, TradingPair

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
