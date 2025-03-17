from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import async_task
from .models import LimitOrder, StopOrder, PriceAlert

def check_and_process_orders():
    """Check and process all open orders"""
    from .management.commands.check_limit_orders import Command
    cmd = Command()
    cmd.handle()

def check_price_alerts():
    """Check price alerts and trigger them if conditions are met"""
    alerts = PriceAlert.objects.filter(triggered=False)
    for alert in alerts:
        current_price = get_current_price(alert.symbol)  # Implement this function to get the current price
        if (alert.target_price >= current_price and alert.symbol == 'buy') or \
           (alert.target_price <= current_price and alert.symbol == 'sell'):
            alert.triggered = True
            alert.save()
            # Notify the user (implement the notification logic)

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

    # Schedule price alert checking every minute
    Schedule.objects.get_or_create(
        func='trading_hub.scheduler.check_price_alerts',
        name='Check Price Alerts',
        defaults={
            'schedule_type': Schedule.MINUTES,
            'minutes': 1,  # Run every minute
            'repeats': -1,  # Repeat indefinitely
            'next_run': timezone.now(),
        }
    )

    print("BitHub order processing and price alert scheduler initialized")