// filepath: d:\the_bit_hub\trading_hub\api\views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
import time

from .serializers import (
    UserSerializer, CryptoCurrencySerializer, WalletSerializer,
    TransactionSerializer, LimitOrderSerializer, StopOrderSerializer,
    NewsSerializer, PriceAlertSerializer, APIKeySerializer
)
from trading_hub.models import (
    CryptoCurrency, Wallet, Transaction, LimitOrder, 
    StopOrder, News, PriceAlert, APIKey, APIRequestLog
)
from .authentication import APIKeyAuthentication
from .permissions import IsAPIKeyReadOnly, IsAPIKeyReadWrite, IsAPIKeyAdmin

class APILoggingMixin:
    """Mixin to log API requests"""
    def dispatch(self, request, *args, **kwargs):
        start_time = time.time()
        response = super().dispatch(request, *args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log the request
        if hasattr(request, 'user') and request.user.is_authenticated:
            api_key = None
            if hasattr(request, 'auth') and isinstance(request.auth, APIKey):
                api_key = request.auth
                
            APIRequestLog.objects.create(
                user=request.user,
                api_key=api_key,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                execution_time=execution_time,
            )
        
        return response

class CryptoCurrencyViewSet(APILoggingMixin, viewsets.ReadOnlyModelViewSet):
    """API endpoint for cryptocurrencies"""
    queryset = CryptoCurrency.objects.all()
    serializer_class = CryptoCurrencySerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = CryptoCurrency.objects.all()
        code = self.request.query_params.get('code')
        if code:
            queryset = queryset.filter(code=code.upper())
        return queryset

class WalletViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for user wallets"""
    serializer_class = WalletSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyReadWrite]
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TransactionViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for user transactions"""
    serializer_class = TransactionSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyReadOnly]
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LimitOrderViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for limit orders"""
    serializer_class = LimitOrderSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyReadWrite]
    
    def get_queryset(self):
        return LimitOrder.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class StopOrderViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for stop orders"""
    serializer_class = StopOrderSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyReadWrite]
    
    def get_queryset(self):
        return StopOrder.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NewsViewSet(APILoggingMixin, viewsets.ReadOnlyModelViewSet):
    """API endpoint for news articles"""
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = News.objects.all()
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__icontains=category)
        # Filter by cryptocurrency
        crypto = self.request.query_params.get('crypto')
        if crypto:
            try:
                crypto_obj = CryptoCurrency.objects.get(code=crypto.upper())
                queryset = queryset.filter(related_cryptocurrencies=crypto_obj)
            except CryptoCurrency.DoesNotExist:
                pass
        return queryset

class PriceAlertViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for price alerts"""
    serializer_class = PriceAlertSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyReadWrite]
    
    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class APIKeyViewSet(APILoggingMixin, viewsets.ModelViewSet):
    """API endpoint for managing API keys"""
    serializer_class = APIKeySerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, IsAPIKeyAdmin]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def api_status(request):
    """Simple endpoint to check API status"""
    return Response({
        'status': 'ok',
        'version': '1.0.0',
        'user': request.user.username,
        'timestamp': timezone.now()
    })

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def market_summary(request):
    """Get a summary of market data for cryptocurrencies"""
    cryptos = CryptoCurrency.objects.all().order_by('-market_cap_usd')[:20]
    serializer = CryptoCurrencySerializer(cryptos, many=True)
    
    return Response({
        'count': cryptos.count(),
        'results': serializer.data,
        'timestamp': timezone.now()
    })