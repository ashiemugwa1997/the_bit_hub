from django.core.management.base import BaseCommand
from django.utils import timezone
from trading_hub.models import LimitOrder

class Command(BaseCommand):
    help = 'Check and execute limit orders that meet their conditions'

    def handle(self, *args, **options):
        # Get all open orders
        open_orders = LimitOrder.objects.filter(status='open')
        
        # Handle expired orders
        expired_orders = open_orders.filter(expires_at__lt=timezone.now())
        expired_count = expired_orders.count()
        expired_orders.update(status='expired')
        
        # Try to execute remaining open orders
        executed_count = 0
        for order in open_orders.exclude(id__in=expired_orders):
            if order.try_execute():
                executed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed limit orders:\n'
                f'- {executed_count} orders executed\n'
                f'- {expired_count} orders expired'
            )
        )