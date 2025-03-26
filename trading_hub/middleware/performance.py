import time
import logging
import re
from django.db import connection
from django.conf import settings

logger = logging.getLogger('performance')

class PerformanceMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Start timing
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # End timing
        duration = time.time() - start_time
        
        # Log slow requests (>1 second)
        if duration > 1:
            path = request.path
            query_count = len(connection.queries)
            
            logger.warning(f"Slow request: {path} took {duration:.2f}s ({query_count} queries)")
            
            # Log the most time-consuming queries
            if query_count > 10:  # If there are many queries, look for N+1 problems
                self._log_queries(connection.queries)
                
        return response
    
    def _log_queries(self, queries):
        # Log duplicate queries that may indicate N+1 problems
        query_patterns = {}
        
        for query in queries:
            # Simplify the query to identify patterns
            simplified = re.sub(r'\d+', 'N', query['sql'])
            simplified = re.sub(r"'[^']*'", "'X'", simplified)
            
            if simplified in query_patterns:
                query_patterns[simplified]['count'] += 1
                query_patterns[simplified]['time'] += float(query['time'])
            else:
                query_patterns[simplified] = {
                    'count': 1,
                    'time': float(query['time']),
                    'example': query['sql']
                }
        
        # Log queries executed many times
        for pattern, data in query_patterns.items():
            if data['count'] > 3:  # More than 3 similar queries suggests an N+1 problem
                logger.warning(f"Potential N+1 problem: {data['count']} similar queries taking {data['time']:.4f}s")
                logger.warning(f"Example query: {data['example'][:200]}...")
