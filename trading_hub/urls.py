from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Assets/Cryptocurrencies
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/<str:code>/', views.crypto_detail, name='crypto_detail'),
    path('assets/<str:code>/buy/', views.buy_crypto, name='buy_crypto'),
    path('assets/<str:code>/sell/', views.sell_crypto, name='sell_crypto'),
    path('assets/<str:code>/send/', views.send_crypto, name='send_crypto'),
    
    # Limit Orders
    path('assets/<str:code>/limit-order/', views.create_limit_order, name='create_limit_order'),
    path('limit-orders/', views.limit_order_list, name='limit_order_list'),
    path('limit-orders/<int:order_id>/', views.limit_order_detail, name='limit_order_detail'),
    
    # Stop Orders
    path('assets/<str:code>/stop-order/', views.create_stop_order, name='create_stop_order'),
    path('stop-orders/', views.stop_order_list, name='stop_order_list'),
    path('stop-orders/<int:order_id>/', views.stop_order_detail, name='stop_order_detail'),
    
    # Recurring Orders
    path('assets/<str:code>/recurring-order/', views.create_recurring_order, name='create_recurring_order'),
    path('recurring-orders/', views.recurring_order_list, name='recurring_order_list'),
    path('recurring-orders/<int:order_id>/', views.recurring_order_detail, name='recurring_order_detail'),
    
    # Transaction history
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # Wallets
    path('wallets/', views.wallet_list, name='wallet_list'),
    
    # Payment methods
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    
    # User profile
    path('profile/', views.profile, name='profile'),
    
    # Order book
    path('order-book/', views.order_book, name='order_book'),
    
    # Depth chart data
    path('depth-chart-data/', views.depth_chart_data, name='depth_chart_data'),
    
    # API endpoints
    # path('api/price-history/<str:code>/<str:period>/', views.price_history_data, name='price_history_data'),
    # path('api/watchlist-toggle/<str:code>/', views.watchlist_toggle, name='watchlist_toggle'),
]
