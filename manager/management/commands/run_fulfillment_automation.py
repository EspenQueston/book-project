"""
Scheduled automation for the order fulfillment system. Run this from cron
every few minutes — it replaces the old behaviour where unpaid-order TTL
rules only ever applied when someone happened to load a specific order page
(there was no scheduler in this codebase at all before this).

Suggested crontab (every 5 minutes):
    */5 * * * * cd /opt/duno360/app && .venv/bin/python manage.py run_fulfillment_automation >> /var/log/duno360/fulfillment.log 2>&1
"""
from django.core.management.base import BaseCommand

from manager import fulfillment_service as fs
from manager.models import Order
from marketplace.models import MarketplaceOrder


class Command(BaseCommand):
    help = 'Run all timed fulfillment automation: unpaid TTL, seller SLA auto-accept, safety-net delivery confirmation, escrow release, refund polling, review requests.'

    def handle(self, *args, **options):
        unpaid_cancelled = 0
        for order in Order.objects.exclude(payment_status='completed').exclude(status__in=('cancelled', 'refunded', 'delivered')).iterator():
            if order.apply_ttl_rules():
                unpaid_cancelled += 1
        for order in MarketplaceOrder.objects.exclude(payment_status='completed').exclude(status__in=('cancelled', 'refunded', 'delivered')).iterator():
            if order.apply_ttl_rules():
                unpaid_cancelled += 1

        auto_accepted = fs.process_seller_sla_auto_accept()
        auto_confirmed = fs.process_auto_confirmations()
        completed = fs.process_due_shipment_completions()
        refunds_updated = fs.process_pending_refunds()
        reviews_sent = fs.send_due_review_requests()

        self.stdout.write(self.style.SUCCESS(
            f'Fulfillment automation done: '
            f'{unpaid_cancelled} unpaid order(s) cancelled, '
            f'{auto_accepted} shipment(s) auto-accepted, '
            f'{auto_confirmed} shipment(s) auto-confirmed delivered, '
            f'{completed} shipment(s) completed (escrow released), '
            f'{refunds_updated} refund(s) updated, '
            f'{reviews_sent} review request(s) sent.'
        ))
