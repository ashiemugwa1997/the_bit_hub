from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import JsonResponse
from decimal import Decimal
from django.utils import timezone
import json
import uuid

from .models import (
    CoinbaseUser,
    Wallet,
    Transaction,
    CryptoCurrency,
    WatchList,
    PriceHistory,
    PaymentMethod,
    LimitOrder,
    StopOrder
)

# Home / Dashboard view
@login_required
def dashboard(request):
    """Main dashboard view similar to Coinbase home"""
    # Get user's wallets and calculate total portfolio value
    wallets = Wallet.objects.filter(user=request.user)
    portfolio_value = Decimal('0.00')
    
    for wallet in wallets:
        try:
            crypto = CryptoCurrency.objects.get(code=wallet.currency_code)
            wallet_value = wallet.balance * crypto.current_price_usd
            portfolio_value += wallet_value
        except CryptoCurrency.DoesNotExist:
            if wallet.currency_code == 'USD':
                portfolio_value += wallet.balance
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get watchlist or create default
    try:
        watchlist = WatchList.objects.get(user=request.user, name="My Watchlist")
    except WatchList.DoesNotExist:
        watchlist = WatchList.objects.create(user=request.user, name="My Watchlist")
        # Add some default cryptocurrencies to watchlist
        default_cryptos = CryptoCurrency.objects.all()[:5]  # First 5 cryptocurrencies
        for crypto in default_cryptos:
            watchlist.currencies.add(crypto)
    
    # Top cryptocurrencies by market cap
    top_cryptos = CryptoCurrency.objects.all().order_by('-market_cap_usd')[:6]
    
    return render(request, 'trading_hub/dashboard.html', {
        'wallets': wallets,
        'portfolio_value': portfolio_value,
        'recent_transactions': recent_transactions,
        'watchlist': watchlist,
        'top_cryptos': top_cryptos,
    })

@login_required
def asset_list(request):
    """View all crypto assets (similar to Coinbase Assets tab)"""
    cryptocurrencies = CryptoCurrency.objects.all().order_by('-market_cap_usd')
    
    # Calculate the user's balance for each cryptocurrency
    user_wallets = Wallet.objects.filter(user=request.user)
    user_balances = {}
    
    for wallet in user_wallets:
        user_balances[wallet.currency_code] = wallet.balance
    
    return render(request, 'trading_hub/asset_list.html', {
        'cryptocurrencies': cryptocurrencies,
        'user_balances': user_balances,
    })

@login_required
def crypto_detail(request, code):
    """Detailed view for a specific cryptocurrency (like Coinbase asset page)"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    
    # Get price history for charts
    price_history = PriceHistory.objects.filter(
        currency=crypto, 
        period='day'
    ).order_by('timestamp')
    
    # Check if user has wallet for this crypto
    try:
        wallet = Wallet.objects.get(user=request.user, currency_code=code)
    except Wallet.DoesNotExist:
        wallet = None
    
    # Get user's transactions for this crypto
    transactions = Transaction.objects.filter(
        user=request.user, 
        currency=code
    ).order_by('-created_at')[:10]
    
    return render(request, 'trading_hub/crypto_detail.html', {
        'crypto': crypto,
        'price_history': price_history,
        'wallet': wallet,
        'transactions': transactions,
    })

@login_required
def buy_crypto(request, code):
    """Buy cryptocurrency view (similar to Coinbase buy flow)"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        payment_method_id = request.POST.get('payment_method')
        
        if amount <= 0:
            return render(request, 'trading_hub/buy_crypto.html', {
                'crypto': crypto,
                'payment_methods': payment_methods,
                'error': 'Please enter a valid amount'
            })
        
        # Calculate the crypto amount based on current price
        crypto_amount = amount / crypto.current_price_usd
        
        # Get or create wallet for this cryptocurrency
        wallet, created = Wallet.objects.get_or_create(
            user=request.user,
            currency_code=code,
            defaults={
                'name': f"My {crypto.name} Wallet",
                'address': f"cb_{uuid.uuid4().hex[:16]}",  # Simplified address generation
            }
        )
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='buy',
            amount=crypto_amount,
            currency=code,
            native_amount=amount,
            native_currency='USD',
            to_wallet=wallet,
            description=f"Bought {crypto_amount} {code}"
        )
        
        # Complete the transaction immediately (in real app would be async)
        transaction.complete_transaction(successful=True)
        
        return redirect('transaction_detail', pk=transaction.id)
    
    return render(request, 'trading_hub/buy_crypto.html', {
        'crypto': crypto,
        'payment_methods': payment_methods,
    })

@login_required
def sell_crypto(request, code):
    """Sell cryptocurrency view (similar to Coinbase sell flow)"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    
    try:
        wallet = Wallet.objects.get(user=request.user, currency_code=code)
    except Wallet.DoesNotExist:
        return redirect('crypto_detail', code=code)
    
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    if request.method == 'POST':
        crypto_amount = Decimal(request.POST.get('amount', 0))
        payment_method_id = request.POST.get('payment_method')
        
        if crypto_amount <= 0:
            return render(request, 'trading_hub/sell_crypto.html', {
                'crypto': crypto,
                'wallet': wallet,
                'payment_methods': payment_methods,
                'error': 'Please enter a valid amount'
            })
        
        if crypto_amount > wallet.balance:
            return render(request, 'trading_hub/sell_crypto.html', {
                'crypto': crypto,
                'wallet': wallet,
                'payment_methods': payment_methods,
                'error': 'Insufficient funds'
            })
        
        # Calculate the fiat amount based on current price
        fiat_amount = crypto_amount * crypto.current_price_usd
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='sell',
            amount=crypto_amount,
            currency=code,
            native_amount=fiat_amount,
            native_currency='USD',
            from_wallet=wallet,
            description=f"Sold {crypto_amount} {code}"
        )
        
        # Complete the transaction immediately (in real app would be async)
        transaction.complete_transaction(successful=True)
        
        return redirect('transaction_detail', pk=transaction.id)
    
    return render(request, 'trading_hub/sell_crypto.html', {
        'crypto': crypto,
        'wallet': wallet,
        'payment_methods': payment_methods,
    })

@login_required
def send_crypto(request, code):
    """Send cryptocurrency to another address (like Coinbase send)"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    
    try:
        wallet = Wallet.objects.get(user=request.user, currency_code=code)
    except Wallet.DoesNotExist:
        return redirect('crypto_detail', code=code)
    
    if request.method == 'POST':
        crypto_amount = Decimal(request.POST.get('amount', 0))
        destination_address = request.POST.get('address', '')
        
        if crypto_amount <= 0:
            return render(request, 'trading_hub/send_crypto.html', {
                'crypto': crypto,
                'wallet': wallet,
                'error': 'Please enter a valid amount'
            })
        
        if crypto_amount > wallet.balance:
            return render(request, 'trading_hub/send_crypto.html', {
                'crypto': crypto,
                'wallet': wallet,
                'error': 'Insufficient funds'
            })
        
        if not destination_address:
            return render(request, 'trading_hub/send_crypto.html', {
                'crypto': crypto,
                'wallet': wallet,
                'error': 'Please enter a destination address'
            })
        
        # Calculate the USD value
        usd_amount = crypto_amount * crypto.current_price_usd
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='send',
            amount=crypto_amount,
            currency=code,
            native_amount=usd_amount,
            native_currency='USD',
            from_wallet=wallet,
            description=f"Sent {crypto_amount} {code} to {destination_address}"
        )
        
        # Complete the transaction immediately (in real app would be async)
        transaction.complete_transaction(successful=True)
        
        return redirect('transaction_detail', pk=transaction.id)
    
    return render(request, 'trading_hub/send_crypto.html', {
        'crypto': crypto,
        'wallet': wallet,
    })

@login_required
def transaction_history(request):
    """View transaction history (like Coinbase Activity tab)"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by type if specified
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    return render(request, 'trading_hub/transaction_history.html', {
        'transactions': transactions,
    })

@login_required
def transaction_detail(request, pk):
    """View details of a specific transaction"""
    transaction = get_object_or_404(Transaction, id=pk, user=request.user)
    
    return render(request, 'trading_hub/transaction_detail.html', {
        'transaction': transaction,
    })

@login_required
def wallet_list(request):
    """View all user wallets (like Coinbase Portfolio tab)"""
    wallets = Wallet.objects.filter(user=request.user)
    total_value = Decimal('0.00')
    
    for wallet in wallets:
        try:
            if wallet.currency_code == 'USD':
                wallet.value_usd = wallet.balance
            else:
                crypto = CryptoCurrency.objects.get(code=wallet.currency_code)
                wallet.value_usd = wallet.balance * crypto.current_price_usd
            total_value += wallet.value_usd
        except CryptoCurrency.DoesNotExist:
            wallet.value_usd = Decimal('0.00')
    
    return render(request, 'trading_hub/wallet_list.html', {
        'wallets': wallets,
        'total_value': total_value,
    })

@login_required
def payment_methods(request):
    """Manage payment methods (like Coinbase Payment Methods)"""
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    
    return render(request, 'trading_hub/payment_methods.html', {
        'payment_methods': payment_methods,
    })

@login_required
def add_payment_method(request):
    """Add a new payment method"""
    if request.method == 'POST':
        method_type = request.POST.get('method_type')
        name = request.POST.get('name')
        last_four = request.POST.get('last_four')
        
        # Create new payment method
        PaymentMethod.objects.create(
            user=request.user,
            method_type=method_type,
            name=name,
            last_four=last_four
        )
        
        return redirect('payment_methods')
    
    return render(request, 'trading_hub/add_payment_method.html')

@login_required
def profile(request):
    """User profile view (like Coinbase Settings)"""
    user_profile = request.user.coinbase_profile
    
    return render(request, 'trading_hub/profile.html', {
        'profile': user_profile,
    })

# API endpoints for chart data
@login_required
def price_history_data(request, code, period='day'):
    """API endpoint to get price history data for charts"""
    try:
        crypto = CryptoCurrency.objects.get(code=code)
        history = PriceHistory.objects.filter(
            currency=crypto,
            period=period
        ).order_by('timestamp')
        
        data = [[int(h.timestamp.timestamp()) * 1000, float(h.price_usd)] for h in history]
        return JsonResponse({'data': data})
    except CryptoCurrency.DoesNotExist:
        return JsonResponse({'error': 'Currency not found'}, status=404)

@login_required
def watchlist_toggle(request, code):
    """Add or remove cryptocurrency from watchlist"""
    if request.method == 'POST':
        try:
            crypto = CryptoCurrency.objects.get(code=code)
            watchlist, created = WatchList.objects.get_or_create(
                user=request.user,
                name="My Watchlist"
            )
            
            if crypto in watchlist.currencies.all():
                watchlist.currencies.remove(crypto)
                added = False
            else:
                watchlist.currencies.add(crypto)
                added = True
            
            return JsonResponse({'added': added})
        except CryptoCurrency.DoesNotExist:
            return JsonResponse({'error': 'Currency not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def create_limit_order(request, code):
    """Create a new limit order"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    
    if request.method == 'POST':
        side = request.POST.get('side')
        amount = Decimal(request.POST.get('amount', '0'))
        limit_price = Decimal(request.POST.get('limit_price', '0'))
        expires_at = request.POST.get('expires_at')
        
        try:
            if side == 'buy':
                # For buy orders, check USD wallet
                from_wallet = Wallet.objects.get(user=request.user, currency_code='USD')
                to_wallet, _ = Wallet.objects.get_or_create(
                    user=request.user,
                    currency_code=code,
                    defaults={
                        'name': f"My {crypto.name} Wallet",
                        'address': f"cb_{uuid.uuid4().hex[:16]}"
                    }
                )
                
                # Check if user has enough USD
                if from_wallet.balance < amount * limit_price:
                    return render(request, 'trading_hub/create_limit_order.html', {
                        'crypto': crypto,
                        'error': 'Insufficient USD balance'
                    })
            else:  # sell
                from_wallet = Wallet.objects.get(user=request.user, currency_code=code)
                to_wallet = Wallet.objects.get(user=request.user, currency_code='USD')
                
                # Check if user has enough crypto
                if from_wallet.balance < amount:
                    return render(request, 'trading_hub/create_limit_order.html', {
                        'crypto': crypto,
                        'error': 'Insufficient crypto balance'
                    })
            
            # Create the limit order
            order = LimitOrder.objects.create(
                user=request.user,
                cryptocurrency=crypto,
                side=side,
                amount=amount,
                limit_price=limit_price,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                expires_at=expires_at if expires_at else None
            )
            
            # Try to execute immediately if conditions are met
            order.try_execute()
            
            return redirect('limit_order_detail', pk=order.id)
            
        except (Wallet.DoesNotExist, ValueError) as e:
            return render(request, 'trading_hub/create_limit_order.html', {
                'crypto': crypto,
                'error': str(e)
            })
    
    return render(request, 'trading_hub/create_limit_order.html', {
        'crypto': crypto,
        'current_price': crypto.current_price_usd
    })

@login_required
def limit_order_list(request):
    """View all limit orders"""
    open_orders = LimitOrder.objects.filter(
        user=request.user,
        status='open'
    ).order_by('-created_at')
    
    filled_orders = LimitOrder.objects.filter(
        user=request.user,
        status='filled'
    ).order_by('-updated_at')[:10]
    
    other_orders = LimitOrder.objects.filter(
        user=request.user,
        status__in=['cancelled', 'expired']
    ).order_by('-updated_at')[:10]
    
    return render(request, 'trading_hub/limit_order_list.html', {
        'open_orders': open_orders,
        'filled_orders': filled_orders,
        'other_orders': other_orders
    })

@login_required
def limit_order_detail(request, pk):
    """View details of a specific limit order"""
    order = get_object_or_404(LimitOrder, id=pk, user=request.user)
    return render(request, 'trading_hub/limit_order_detail.html', {'order': order})

@login_required
def cancel_limit_order(request, pk):
    """Cancel a limit order"""
    if request.method == 'POST':
        order = get_object_or_404(LimitOrder, id=pk, user=request.user)
        if order.cancel():
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Order cannot be cancelled'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def check_limit_orders():
    """Background task to check and execute limit orders"""
    open_orders = LimitOrder.objects.filter(status='open')
    
    # Handle expired orders
    expired_orders = open_orders.filter(expires_at__lt=timezone.now())
    expired_orders.update(status='expired')
    
    # Try to execute remaining open orders
    for order in open_orders.exclude(id__in=expired_orders):
        order.try_execute()

@login_required
def create_stop_order(request, code):
    """Create a new stop order"""
    crypto = get_object_or_404(CryptoCurrency, code=code)
    is_stop_limit = request.GET.get('stop_limit') == 'true'
    
    if request.method == 'POST':
        side = request.POST.get('side')
        amount = Decimal(request.POST.get('amount', '0'))
        stop_price = Decimal(request.POST.get('stop_price', '0'))
        limit_price = request.POST.get('limit_price') if is_stop_limit else None
        expires_at = request.POST.get('expires_at')

        if limit_price:
            limit_price = Decimal(limit_price)
            # Validate stop and limit prices
            if side == 'buy' and limit_price >= stop_price:
                return render(request, 'trading_hub/create_stop_order.html', {
                    'crypto': crypto,
                    'error': 'Limit price must be below stop price for buy orders'
                })
            elif side == 'sell' and limit_price <= stop_price:
                return render(request, 'trading_hub/create_stop_order.html', {
                    'crypto': crypto,
                    'error': 'Limit price must be above stop price for sell orders'
                })
        
        try:
            if side == 'buy':
                # For buy orders, check USD wallet
                from_wallet = Wallet.objects.get(user=request.user, currency_code='USD')
                to_wallet, _ = Wallet.objects.get_or_create(
                    user=request.user,
                    currency_code=code,
                    defaults={
                        'name': f"My {crypto.name} Wallet",
                        'address': f"cb_{uuid.uuid4().hex[:16]}"
                    }
                )
                
                # Check if user has enough USD (using stop price for calculation)
                estimated_cost = amount * stop_price
                if from_wallet.balance < estimated_cost:
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'error': 'Insufficient USD balance'
                    })
                
                # Validate stop price
                if stop_price <= crypto.current_price_usd:
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'error': 'Buy stop price must be above current market price'
                    })
            else:  # sell
                from_wallet = Wallet.objects.get(user=request.user, currency_code=code)
                to_wallet = Wallet.objects.get(user=request.user, currency_code='USD')
                
                # Check if user has enough crypto
                if from_wallet.balance < amount:
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'error': 'Insufficient crypto balance'
                    })
                
                # Validate stop price
                if stop_price >= crypto.current_price_usd:
                    return render(request, 'trading_hub/create_stop_order.html', {
                        'crypto': crypto,
                        'error': 'Sell stop price must be below current market price'
                    })
            
            # Create the stop order
            order = StopOrder.objects.create(
                user=request.user,
                cryptocurrency=crypto,
                side=side,
                amount=amount,
                stop_price=stop_price,
                limit_price=limit_price,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                expires_at=expires_at if expires_at else None
            )
            
            # Try to trigger immediately if conditions are met
            order.try_trigger()
            
            return redirect('stop_order_detail', pk=order.id)
            
        except (Wallet.DoesNotExist, ValueError) as e:
            return render(request, 'trading_hub/create_stop_order.html', {
                'crypto': crypto,
                'error': str(e)
            })
    
    return render(request, 'trading_hub/create_stop_order.html', {
        'crypto': crypto,
        'current_price': crypto.current_price_usd
    })

@login_required
def stop_order_list(request):
    """View all stop orders"""
    open_orders = StopOrder.objects.filter(
        user=request.user,
        status='open'
    ).order_by('-created_at')
    
    triggered_orders = StopOrder.objects.filter(
        user=request.user,
        status='triggered'
    ).order_by('-updated_at')[:10]
    
    filled_orders = StopOrder.objects.filter(
        user=request.user,
        status='filled'
    ).order_by('-updated_at')[:10]
    
    other_orders = StopOrder.objects.filter(
        user=request.user,
        status__in=['cancelled', 'expired']
    ).order_by('-updated_at')[:10]
    
    return render(request, 'trading_hub/stop_order_list.html', {
        'open_orders': open_orders,
        'triggered_orders': triggered_orders,
        'filled_orders': filled_orders,
        'other_orders': other_orders
    })

@login_required
def stop_order_detail(request, pk):
    """View details of a specific stop order"""
    order = get_object_or_404(StopOrder, id=pk, user=request.user)
    return render(request, 'trading_hub/stop_order_detail.html', {'order': order})

@login_required
def cancel_stop_order(request, pk):
    """Cancel a stop order"""
    if request.method == 'POST':
        order = get_object_or_404(StopOrder, id=pk, user=request.user)
        if order.cancel():
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Order cannot be cancelled'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def check_stop_orders():
    """Background task to check and execute stop orders"""
    open_orders = StopOrder.objects.filter(status='open')
    
    # Handle expired orders
    expired_orders = open_orders.filter(expires_at__lt=timezone.now())
    expired_orders.update(status='expired')
    
    # Try to trigger remaining open orders
    for order in open_orders.exclude(id__in=expired_orders):
        order.try_trigger()
