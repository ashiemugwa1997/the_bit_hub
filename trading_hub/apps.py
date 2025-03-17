from django.apps import AppConfig


class TradingHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trading_hub'
    
    def ready(self):
        """Initialize app components when Django starts"""
        # Don't run when collecting static files
        import sys
        if 'collectstatic' not in sys.argv and 'makemigrations' not in sys.argv and 'migrate' not in sys.argv:
            try:
                # Re-enable the scheduler setup
                from .scheduler import setup_scheduler
                setup_scheduler()
                print("Scheduler initialized successfully")
            except ImportError as e:
                print(f"Warning: Could not initialize scheduler due to import error: {e}")
                print("The application will run, but scheduled tasks will not be available.")
