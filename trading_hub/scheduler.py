from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import async_task
from .models import LimitOrder, StopOrder

def check_and_process_orders():
    """Check and process all open orders"""
    from .management.commands.check_limit_orders import Command
    cmd = Command()
    cmd.handle()

def setup_scheduler():
    """Set up all scheduled tasks for the trading hub app"""
    # Schedule order checking every minute
    Schedule.objects.get_or_create(
        func='trading_hub.scheduler.check_and_process_orders',
        name='Process Trading Orders',
        defaults={
            'schedule_type': Schedule.MINUTES,
            'minutes': 1,  # Run every minute
            'repeats': -1,  # Repeat indefinitely
            'next_run': timezone.now(),
        }
    )
    print("BitHub order processing scheduler initialized")