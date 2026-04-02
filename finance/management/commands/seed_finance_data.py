from datetime import timedelta
from decimal import Decimal
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from finance.models import Expense, ExpenseCategory
from finance.services import ensure_receipt_default_allocation, generate_statement_runs, recalculate_customer_invoices
from sales.models import Customer
from sales.models import Receipt


DEFAULT_CATEGORIES = [
    'Operations',
    'Office Supplies',
    'Utilities',
    'Transport',
    'Marketing',
    'Professional Fees',
    'Software',
    'Maintenance',
    'Payroll Support',
    'Miscellaneous',
]


class Command(BaseCommand):
    help = 'Seed finance categories and optional sample expenses, allocations, and statement runs.'

    def add_arguments(self, parser):
        parser.add_argument('--sample-expenses', type=int, default=0, help='Number of sample expenses to create')
        parser.add_argument('--with-allocations', action='store_true', help='Create default allocations for existing receipts')
        parser.add_argument('--with-statement-runs', action='store_true', help='Generate statement runs for last month')

    def handle(self, *args, **options):
        fake = Faker()
        sample_expenses = options['sample_expenses']

        created_categories = 0
        for category_name in DEFAULT_CATEGORIES:
            _, created = ExpenseCategory.objects.get_or_create(name=category_name)
            if created:
                created_categories += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_categories} new expense categories'))

        user, _ = User.objects.get_or_create(
            username='finance-bot',
            defaults={'email': 'finance-bot@example.com', 'is_staff': True},
        )
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save(update_fields=['password'])

        if sample_expenses > 0:
            categories = list(ExpenseCategory.objects.filter(is_active=True))
            payment_methods = [choice[0] for choice in Expense.PAYMENT_METHOD_CHOICES]
            expense_titles = [
                'Office Internet',
                'Printer Consumables',
                'Team Transport',
                'Cloud Hosting',
                'Design Subscription',
                'Maintenance Callout',
                'Client Meeting Catering',
                'Electricity Bill',
                'Cleaning Services',
                'Domain Renewal',
            ]

            created_expenses = 0
            for _ in range(sample_expenses):
                amount = Decimal(str(round(random.uniform(75, 4500), 2)))
                expense_date = timezone.localdate() - timedelta(days=random.randint(0, 180))
                Expense.objects.create(
                    title=random.choice(expense_titles),
                    category=random.choice(categories) if categories else None,
                    amount=amount,
                    expense_date=expense_date,
                    vendor=fake.company(),
                    payment_method=random.choice(payment_methods),
                    reference_number=fake.bothify('EXP-####-??'),
                    notes=fake.sentence(nb_words=10),
                    created_by=user,
                )
                created_expenses += 1

            self.stdout.write(self.style.SUCCESS(f'Created {created_expenses} sample expenses'))

        if options['with_allocations']:
            count = 0
            customers = set()
            for receipt in Receipt.objects.select_related('customer').all():
                ensure_receipt_default_allocation(receipt)
                customers.add(receipt.customer_id)
                count += 1
            for customer_id in customers:
                customer = Customer.objects.filter(pk=customer_id).first()
                if customer:
                    recalculate_customer_invoices(customer)
            self.stdout.write(self.style.SUCCESS(f'Processed default allocations for {count} receipt(s)'))

        if options['with_statement_runs']:
            today = timezone.localdate()
            period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            period_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            runs = generate_statement_runs(period_start, period_end, generated_by=user)
            self.stdout.write(self.style.SUCCESS(f'Generated {len(runs)} statement run record(s)'))