from django.http import HttpResponseForbidden
from django.conf import settings

class IPAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_ips = getattr(settings, 'ALLOWED_IPS', [])

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')
        if ip not in self.allowed_ips:
            return HttpResponseForbidden('Forbidden: Your IP is not allowed.')
        return self.get_response(request)
