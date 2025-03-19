from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'cryptocurrencies', views.CryptoCurrencyViewSet)
router.register(r'wallets', views.WalletViewSet, basename='wallet')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'limit-orders', views.LimitOrderViewSet, basename='limitorder')
router.register(r'stop-orders', views.StopOrderViewSet, basename='stoporder')
router.register(r'news', views.NewsViewSet)
router.register(r'price-alerts', views.PriceAlertViewSet, basename='pricealert')
router.register(r'api-keys', views.APIKeyViewSet, basename='apikey')

# API Documentation
schema_view = get_schema_view(
   openapi.Info(
      title="BitHub API",
      default_version='v1',
      description="API for BitHub cryptocurrency trading platform",
      terms_of_service="https://www.bithub.com/terms/",
      contact=openapi.Contact(email="developers@bithub.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('status/', views.api_status, name='api_status'),
    path('market-summary/', views.market_summary, name='market_summary'),
    
    # API Documentation
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]