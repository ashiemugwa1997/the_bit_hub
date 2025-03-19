from django.urls import path, include
from . import views
from .views import PriceAlertListView, PriceAlertCreateView, PriceAlertUpdateView, PriceAlertDeleteView

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

    # Price alerts
    path('price-alerts/', PriceAlertListView.as_view(), name='price_alert_list'),
    path('price-alerts/create/', PriceAlertCreateView.as_view(), name='price_alert_create'),
    path('price-alerts/<int:pk>/update/', PriceAlertUpdateView.as_view(), name='price_alert_update'),
    path('price-alerts/<int:pk>/delete/', PriceAlertDeleteView.as_view(), name='price_alert_delete'),

    # Mobile integration
    path('mobile/dashboard/', views.mobile_dashboard, name='mobile_dashboard'),
    path('mobile/assets/', views.mobile_asset_list, name='mobile_asset_list'),
    path('mobile/assets/<str:code>/', views.mobile_crypto_detail, name='mobile_crypto_detail'),
    path('mobile/transactions/', views.mobile_transaction_history, name='mobile_transaction_history'),
    path('mobile/profile/', views.mobile_profile, name='mobile_profile'),

    # User registration
    path('register/', views.register_user, name='register_user'),
    
    # Educational resources
    path('learn/', views.education_home, name='education_home'),
    path('learn/trading-basics/', views.trading_basics, name='trading_basics'),
    path('learn/crypto-fundamentals/', views.crypto_fundamentals, name='crypto_fundamentals'),
    path('learn/technical-analysis/', views.technical_analysis, name='technical_analysis'),
    path('learn/risk-management/', views.risk_management, name='risk_management'),
    path('learn/platform-guide/', views.platform_guide, name='platform_guide'),

    # Add conversion URLs
    path('convert/', views.conversion_pairs, name='conversion_pairs'),
    path('convert/<str:from_code>/<str:to_code>/', views.convert_crypto, name='convert_crypto'),
    path('api/conversion-rate/<str:from_code>/<str:to_code>/', views.get_conversion_rate, name='get_conversion_rate'),
]

urlpatterns += [
    # News feed
    path('news/', views.news_feed, name='news_feed'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),
    path('news/category/<str:category>/', views.news_category, name='news_category'),
    path('news/crypto/<str:code>/', views.news_by_crypto, name='news_by_crypto'),
    path('news/insights/', views.market_insights, name='market_insights'),
]

urlpatterns += [
    # API management
    path('api/keys/', views.api_key_list, name='api_key_list'),
    path('api/keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
    path('api/keys/<uuid:pk>/', views.APIKeyDetailView.as_view(), name='api_key_detail'),
    path('api/keys/<uuid:pk>/update/', views.APIKeyUpdateView.as_view(), name='api_key_update'),
    path('api/keys/<uuid:pk>/delete/', views.APIKeyDeleteView.as_view(), name='api_key_delete'),
    path('api/keys/<uuid:pk>/regenerate/', views.api_key_regenerate_secret, name='api_key_regenerate'),
    path('api/docs/', views.api_documentation, name='api_documentation'),
    
    # API endpoints
    path('api/v1/', include('trading_hub.api.urls')),
]

# Add API patterns only if rest_framework is installed
api_patterns = []
try:
    import rest_framework
    api_patterns = [
        # API management
        path('api/keys/', views.api_key_list, name='api_key_list'),
        path('api/keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
        path('api/keys/<uuid:pk>/', views.APIKeyDetailView.as_view(), name='api_key_detail'),
        path('api/keys/<uuid:pk>/update/', views.APIKeyUpdateView.as_view(), name='api_key_update'),
        path('api/keys/<uuid:pk>/delete/', views.APIKeyDeleteView.as_view(), name='api_key_delete'),
        path('api/keys/<uuid:pk>/regenerate/', views.api_key_regenerate_secret, name='api_key_regenerate'),
        path('api/docs/', views.api_documentation, name='api_documentation'),
    ]
    
    # Try to include API v1 endpoints
    try:
        api_patterns.append(path('api/v1/', include('trading_hub.api.urls')))
    except (ImportError, ModuleNotFoundError):
        pass
        
except ImportError:
    # REST framework not installed, API functionality will be limited
    pass

urlpatterns += api_patterns

# Add tax reporting URLs
urlpatterns += [
    # Tax reporting center
    path('taxes/', views.tax_center, name='tax_center'),
    path('taxes/create-report/', views.create_tax_report, name='create_tax_report'),
    path('taxes/reports/<uuid:report_id>/', views.tax_report_detail, name='tax_report_detail'),
    path('taxes/reports/<uuid:report_id>/download/', views.download_tax_report, name='download_tax_report'),
    path('taxes/summary/', views.annual_tax_summary, name='annual_tax_summary'),  # Default route
    path('taxes/summary/<int:year>/', views.annual_tax_summary, name='annual_tax_summary_with_year'),
    path('taxes/calculator/', views.cost_basis_calculator, name='cost_basis_calculator'),
    path('api/taxes/calculate-cost-basis/', views.api_calculate_cost_basis, name='api_calculate_cost_basis'),
]
