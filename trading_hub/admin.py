from django.contrib import admin
from .models import TraderProfile, Trade

# Register TraderProfile with custom admin display
@admin.register(TraderProfile)
class TraderProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'total_trades', 'successful_trades')
    search_fields = ('user__username',)
    list_filter = ('rating',)
    readonly_fields = ('rating', 'total_trades', 'successful_trades')

# Register Trade with custom admin display
@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('user', 'trade_type', 'amount', 'price', 'date', 'is_successful')
    list_filter = ('trade_type', 'is_successful', 'date')
    search_fields = ('user__username',)
    date_hierarchy = 'date'
```
# Register your models here.
