from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from trading_hub.models import APIKey
import hmac
import hashlib
import time

class APIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication for REST API using API keys.
    
    The client must include the following headers:
    - X-API-Key: The API key
    - X-API-Signature: HMAC signature of the request
    - X-API-Timestamp: Current timestamp (to prevent replay attacks)
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            api_key_obj = APIKey.objects.get(key=api_key, is_active=True)
            
            # Check if key has expired
            if api_key_obj.is_expired():
                raise AuthenticationFailed('API key has expired')
            
            # Check if IP is allowed
            client_ip = request.META.get('REMOTE_ADDR')
            if not api_key_obj.has_valid_ip(client_ip):
                raise AuthenticationFailed('IP address not allowed for this API key')
            
            # Verify the signature
            signature = request.META.get('HTTP_X_API_SIGNATURE')
            timestamp = request.META.get('HTTP_X_API_TIMESTAMP')
            
            if not all([signature, timestamp]):
                raise AuthenticationFailed('Missing required authentication parameters')
            
            # Check timestamp is within acceptable window (5 minutes)
            try:
                timestamp_int = int(timestamp)
                current_time = int(time.time())
                if abs(current_time - timestamp_int) > 300:  # 5 minutes window
                    raise AuthenticationFailed('Request timestamp too skewed')
            except ValueError:
                raise AuthenticationFailed('Invalid timestamp format')
            
            # Verify signature
            string_to_sign = f"{timestamp}{request.method}{request.path}"
            if request.body:
                string_to_sign += request.body.decode('utf-8')
            
            expected_signature = hmac.new(
                api_key_obj.secret.encode(), 
                string_to_sign.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise AuthenticationFailed('Invalid signature')
            
            # Update last used timestamp
            api_key_obj.last_used = timezone.now()
            api_key_obj.save(update_fields=['last_used'])
            
            return (api_key_obj.user, api_key_obj)
            
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')
    
    def authenticate_header(self, request):
        return 'APIKey'