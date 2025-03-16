from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Trade, TraderProfile
from .forms import TradeForm
from .utils import get_bitcoin_price

@login_required
def trade_list(request):
    trades = Trade.objects.filter(user=request.user)
    # Get current user's trader profile
    trader_profile = request.user.trader_profile
    return render(request, 'trading_hub/trade_list.html', {
        'trades': trades,
        'trader_profile': trader_profile
    })

@login_required
def create_trade(request):
    if request.method == 'POST':
        form = TradeForm(request.POST)
        if form.is_valid():
            trade = form.save(commit=False)
            trade.user = request.user
            trade.price = get_bitcoin_price()
            trade.save()
            return redirect('trade_list')
    else:
        form = TradeForm()
    return render(request, 'trading_hub/create_trade.html', {'form': form})

@login_required
def complete_trade(request, trade_id):
    """Mark a trade as complete and update trader rating"""
    trade = get_object_or_404(Trade, id=trade_id, user=request.user)
    success = request.GET.get('success', 'true').lower() == 'true'
    
    trade.complete_trade(successful=success)
    return redirect('trade_list')

@login_required
def trader_profile(request, username):
    """View another trader's profile and rating"""
    trader = get_object_or_404(User, username=username)
    trader_profile = trader.trader_profile
    trades = Trade.objects.filter(user=trader)
    
    return render(request, 'trading_hub/trader_profile.html', {
        'trader': trader,
        'trader_profile': trader_profile,
        'trades': trades
    })

@login_required
def top_traders(request):
    """View a list of traders sorted by rating"""
    top_traders = TraderProfile.objects.order_by('-rating')[:10]
    return render(request, 'trading_hub/top_traders.html', {
        'top_traders': top_traders
    })
