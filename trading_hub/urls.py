from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Assets/Cryptocurrencies
    path('assets/', views.asset_list, name='asset_list'),
    path('asset/<str:code>/', views.crypto_detail, name='crypto_detail'),
    
    # Trading functionality
    path('buy/<str:code>/', views.buy_crypto, name='buy_crypto'),
    path('sell/<str:code>/', views.sell_crypto, name='sell_crypto'),
    path('send/<str:code>/', views.send_crypto, name='send_crypto'),
    
    # Limit Orders
    path('limit-order/<str:code>/create/', views.create_limit_order, name='create_limit_order'),
    path('limit-orders/', views.limit_order_list, name='limit_order_list'),
    path('limit-order/<uuid:pk>/', views.limit_order_detail, name='limit_order_detail'),
    path('limit-order/<uuid:pk>/cancel/', views.cancel_limit_order, name='cancel_limit_order'),
    
    # Stop Orders
    path('stop-order/<str:code>/create/', views.create_stop_order, name='create_stop_order'),
    path('stop-orders/', views.stop_order_list, name='stop_order_list'),
    path('stop-order/<uuid:pk>/', views.stop_order_detail, name='stop_order_detail'),
    path('stop-order/<uuid:pk>/cancel/', views.cancel_stop_order, name='cancel_stop_order'),
    
    # Transaction history
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('transaction/<uuid:pk>/', views.transaction_detail, name='transaction_detail'),
    
    # Wallets
    path('wallets/', views.wallet_list, name='wallet_list'),
    
    # Payment methods
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    
    # User profile
    path('profile/', views.profile, name='profile'),
    
    # API endpoints
    path('api/price-history/<str:code>/<str:period>/', views.price_history_data, name='price_history_data'),
    path('api/watchlist-toggle/<str:code>/', views.watchlist_toggle, name='watchlist_toggle'),
]
