from django import template
from django.core.cache import cache
from django.utils.safestring import mark_safe
import hashlib

register = template.Library()

@register.tag('cache_fragment')
def do_cache(parser, token):
    """
    Template tag to cache fragments
    
    Usage:
    {% load cache_utils %}
    {% cache_fragment [fragment_name] [timeout_seconds] %}
        ...expensive template content...
    {% endcache_fragment %}
    """
    # Parse the tag tokens
    tokens = token.split_contents()
    if len(tokens) < 2:
        raise template.TemplateSyntaxError(
            "%r tag requires at least a fragment name." % tokens[0]
        )
    
    fragment_name = tokens[1]
    timeout = 300  # Default: 5 minutes
    
    if len(tokens) >= 3:
        try:
            timeout = int(tokens[2])
        except ValueError:
            timeout = template.Variable(tokens[2])
    
    nodelist = parser.parse(('endcache_fragment',))
    parser.delete_first_token()
    return CacheNode(nodelist, fragment_name, timeout)

class CacheNode(template.Node):
    def __init__(self, nodelist, fragment_name, timeout):
        self.nodelist = nodelist
        self.fragment_name = template.Variable(fragment_name)
        self.timeout = timeout
    
    def render(self, context):
        try:
            fragment_name = self.fragment_name.resolve(context)
        except template.VariableDoesNotExist:
            fragment_name = self.fragment_name
            
        # Create a cache key
        cache_key = f"template_fragment_{fragment_name}"
        
        # Try to get the cached content
        content = cache.get(cache_key)
        if content is not None:
            return mark_safe(content)
        
        # Render the content if not cached
        content = self.nodelist.render(context)
        
        # Resolve timeout if it's a variable
        timeout = self.timeout
        if isinstance(timeout, template.Variable):
            try:
                timeout = timeout.resolve(context)
            except template.VariableDoesNotExist:
                timeout = 300
                
        # Cache the content
        cache.set(cache_key, content, timeout)
        return mark_safe(content)
