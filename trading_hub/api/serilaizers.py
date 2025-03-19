// filepath: d:\the_bit_hub\trading_hub\api\serializers.py
from rest_framework import serializers
from trading_hub.models import (
    CryptoCurrency, Wallet, Transaction, 
    LimitOrder, StopOrder, News, PriceAlert,
    APIKey
)
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')
        read_only_fields = fields

class CryptoCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoCurrency
        fields = '__all__'

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'currency_code', 'name', 'balance', 'address', 'created_at')
        read_only_fields = ('id', 'address', 'created_at')

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        exclude = ('user',)
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')

class LimitOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LimitOrder
        exclude = ('user',)
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')

class StopOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopOrder
        exclude = ('user',)
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        exclude = ('user',)
        read_only_fields = ('id', 'created_at', 'triggered')

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ('id', 'name', 'key', 'permissions', 'created_at', 
                  'last_used', 'expires_at', 'is_active', 'allowed_ips')
        read_only_fields = ('id', 'key', 'created_at', 'last_used')