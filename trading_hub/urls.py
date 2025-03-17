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
    
    # Device management
    path('devices/', views.device_list, name='device_list'),
    path('devices/register/', views.device_register, name='device_register'),
    path('devices/remove/<str:device_id>/', views.device_remove, name='device_remove'),
    
    # KYC
    path('kyc/submit/', views.submit_kyc, name='kyc_submit'),
    path('kyc/status/', views.kyc_status, name='kyc_status'),
    path('kyc/list/', views.kyc_list, name='kyc_list'),
    path('kyc/verify/<int:kyc_id>/', views.verify_kyc, name='kyc_verify'),
    path('kyc/verify_tier/<int:kyc_id>/', views.verify_tier, name='verify_tier'),
    path('verify-tier-1/', views.verify_tier_1, name='verify_tier_1'),
    path('verify-tier-2/', views.verify_tier_2, name='verify_tier_2'),
    path('verify-tier-3/', views.verify_tier_3, name='verify_tier_3'),
    
    # Address submission and verification
    path('address/submit/', views.submit_address, name='address_submit'),
    path('address/verify/<int:kyc_id>/', views.verify_address, name='address_verify'),
    
    # Bank accounts
    path('bank_accounts/', views.bank_account_list, name='bank_account_list'),
    path('bank_accounts/add/', views.add_bank_account, name='add_bank_account'),
    path('bank_accounts/update/<int:pk>/', views.update_bank_account, name='update_bank_account'),
    path('bank_accounts/delete/<int:pk>/', views.delete_bank_account, name='delete_bank_account'),
    
    # API endpoints
    # path('api/price-history/<str:code>/<str:period>/', views.price_history_data, name='price_history_data'),
    # path('api/watchlist-toggle/<str:code>/', views.watchlist_toggle, name='watchlist_toggle'),

    # Wire transfer
    path('initiate-wire-transfer/', views.initiate_wire_transfer, name='initiate_wire_transfer'),
]
