from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from sales.models import Customer

from finance.services import generate_statement_runs


class Command(BaseCommand):
    help = 'Generate statement run records for a monthly period.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Target year for statement period')
        parser.add_argument('--month', type=int, help='Target month (1-12) for statement period')
        parser.add_argument('--customer-id', type=int, help='Generate for one customer only')
        parser.add_argument('--generated-by', type=str, default='finance-bot', help='Username recorded as generator')

    def handle(self, *args, **options):
        if options['year'] and options['month']:
            period_start = timezone.datetime(options['year'], options['month'], 1).date()
        else:
            today = timezone.localdate()
            period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        customer = None
        if options['customer_id']:
            customer = Customer.objects.filter(pk=options['customer_id']).first()
            if not customer:
                self.stdout.write(self.style.ERROR('Customer not found'))
                return

        generated_by = User.objects.filter(username=options['generated_by']).first()
        runs = generate_statement_runs(period_start, period_end, generated_by=generated_by, customer=customer)

        self.stdout.write(self.style.SUCCESS(
            f'Generated {len(runs)} statement run record(s) for {period_start} to {period_end}.'
        ))
