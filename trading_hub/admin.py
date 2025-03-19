from django.contrib import admin
from django.utils.translation import gettext as _
from .models import (
    CoinbaseUser,
    Wallet,
    Transaction,
    CryptoCurrency,
    WatchList,
    PriceHistory,
    PaymentMethod,
    LimitOrder,
    StopOrder,
    News  # Add the News model import here
)

# Register CoinbaseUser with custom admin display
@admin.register(CoinbaseUser)
class CoinbaseUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'total_trades', 'successful_trades', 'phone_verified', 'identity_verified')
    search_fields = ('user__username', 'user__email')
    list_filter = ('rating', 'phone_verified', 'identity_verified')
    readonly_fields = ('rating', 'total_trades', 'successful_trades')

# Register Wallet with custom admin display
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency_code', 'name', 'balance', 'created_at')
    search_fields = ('user__username', 'currency_code', 'address')
    list_filter = ('currency_code', 'created_at')

# Register Transaction with custom admin display
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'currency', 'native_amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'currency', 'created_at')
    search_fields = ('user__username', 'description', 'id')
    date_hierarchy = 'created_at'

# Register CryptoCurrency with custom admin display
@admin.register(CryptoCurrency)
class CryptoCurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'current_price_usd', 'price_change_24h_percent', 'last_updated')
    search_fields = ('code', 'name')
    list_filter = ('last_updated',)

# Register WatchList
@admin.register(WatchList)
class WatchListAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'created_at')
    search_fields = ('user__username', 'name')
    filter_horizontal = ('currencies',)

# Register PriceHistory
@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('currency', 'price_usd', 'timestamp', 'period')
    list_filter = ('currency', 'period', 'timestamp')
    date_hierarchy = 'timestamp'

# Register PaymentMethod
@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'method_type', 'provider', 'account_number', 'created_at']
    list_filter = ['method_type', 'provider']
    search_fields = ['user__username', 'provider', 'account_number']

# Register LimitOrder
@admin.register(LimitOrder)
class LimitOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'cryptocurrency', 'side', 'amount', 'limit_price', 'status', 'created_at')
    list_filter = ('status', 'side', 'cryptocurrency', 'created_at')
    search_fields = ('user__username', 'cryptocurrency__code', 'cryptocurrency__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')

# Register StopOrder
@admin.register(StopOrder)
class StopOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'cryptocurrency', 'side', 'amount', 'stop_price', 'limit_price', 'status', 'created_at')
    list_filter = ('status', 'side', 'cryptocurrency', 'created_at')
    search_fields = ('user__username', 'cryptocurrency__code', 'cryptocurrency__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'sentiment', 'featured')
    list_filter = ('source', 'sentiment', 'featured', 'published_at')
    search_fields = ('title', 'content', 'source')
    filter_horizontal = ('related_cryptocurrencies',)
    date_hierarchy = 'published_at'
    list_editable = ('featured', 'sentiment')
