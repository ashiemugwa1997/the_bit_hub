from django.core.management.base import BaseCommand
from django.utils import timezone
from trading_hub.models import LimitOrder, StopOrder

class Command(BaseCommand):
    help = 'Check and execute limit and stop orders that meet their conditions'

    def handle(self, *args, **options):
        # Handle limit orders
        open_limit_orders = LimitOrder.objects.filter(status='open')
        
        # Handle expired limit orders
        expired_limit_orders = open_limit_orders.filter(expires_at__lt=timezone.now())
        expired_limit_count = expired_limit_orders.count()
        expired_limit_orders.update(status='expired')
        
        # Try to execute remaining open limit orders
        executed_limit_count = 0
        for order in open_limit_orders.exclude(id__in=expired_limit_orders):
            if order.try_execute():
                executed_limit_count += 1
        
        # Handle stop orders
        open_stop_orders = StopOrder.objects.filter(status='open')
        
        # Handle expired stop orders
        expired_stop_orders = open_stop_orders.filter(expires_at__lt=timezone.now())
        expired_stop_count = expired_stop_orders.count()
        expired_stop_orders.update(status='expired')
        
        # Try to trigger remaining open stop orders
        triggered_stop_count = 0
        for order in open_stop_orders.exclude(id__in=expired_stop_orders):
            if order.try_trigger():
                triggered_stop_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed orders:\n'
                f'Limit Orders:\n'
                f'- {executed_limit_count} orders executed\n'
                f'- {expired_limit_count} orders expired\n'
                f'Stop Orders:\n'
                f'- {triggered_stop_count} orders triggered\n'
                f'- {expired_stop_count} orders expired'
            )
        )