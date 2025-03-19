// filepath: d:\the_bit_hub\trading_hub\api\permissions.py
from rest_framework import permissions
from trading_hub.models import APIKey

class IsAPIKeyReadOnly(permissions.BasePermission):
    """
    Permission class for API keys with read-only access
    """
    
    def has_permission(self, request, view):
        if not request.auth or not isinstance(request.auth, APIKey):
            return False
            
        # Allow GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Deny write operations
        return False

class IsAPIKeyReadWrite(permissions.BasePermission):
    """
    Permission class for API keys with read-write access
    """
    
    def has_permission(self, request, view):
        if not request.auth or not isinstance(request.auth, APIKey):
            return False
            
        # Allow GET, HEAD, OPTIONS for any permission level
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Allow write operations only for read_write or admin keys
        return request.auth.permissions in ['read_write', 'admin']

class IsAPIKeyAdmin(permissions.BasePermission):
    """
    Permission class for API keys with admin access
    """
    
    def has_permission(self, request, view):
        if not request.auth or not isinstance(request.auth, APIKey):
            return False
            
        # Allow only for admin keys
        return request.auth.permissions == 'admin'