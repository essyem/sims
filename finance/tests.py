from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from finance.models import Expense, ExpenseCategory, PaymentAllocation, StatementRun
from sales.models import Customer, Invoice, Receipt


class FinanceViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='secret123')
        self.client.login(username='tester', password='secret123')
        self.customer = Customer.objects.create(name='Acme Ltd', phone='12345', email='acme@example.com')
        self.invoice = Invoice.objects.create(
            invoice_number='INV-00001',
            customer=self.customer,
            created_by=self.user,
            status='sent',
            invoice_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=5),
            tax_rate=Decimal('0.00'),
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('250.00'),
        )
        Receipt.objects.create(
            receipt_number='REC-00001',
            invoice=self.invoice,
            customer=self.customer,
            amount=Decimal('250.00'),
            payment_method='bank_transfer',
            payment_date=date.today() - timedelta(days=10),
            created_by=self.user,
        )

    def test_customer_statement_page_renders(self):
        response = self.client.get(reverse('finance:customer-statement'), {'customer': self.customer.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer Statement')
        self.assertContains(response, 'INV-00001')
        self.assertContains(response, 'REC-00001')

    def test_customer_statement_pdf_downloads(self):
        response = self.client.get(reverse('finance:customer-statement-pdf', args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_expense_create_page_creates_expense(self):
        category = ExpenseCategory.objects.create(name='Operations')
        response = self.client.post(reverse('finance:expense-create'), {
            'title': 'Office Internet',
            'category': category.pk,
            'amount': '350.00',
            'expense_date': date.today().isoformat(),
            'vendor': 'ISP',
            'payment_method': 'card',
            'reference_number': 'REF-1',
            'notes': 'Monthly bill',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Expense.objects.filter(title='Office Internet').exists())

    def test_seed_finance_command_creates_categories_and_expenses(self):
        output = StringIO()
        call_command('seed_finance_data', sample_expenses=3, with_allocations=True, with_statement_runs=True, stdout=output)
        self.assertGreaterEqual(ExpenseCategory.objects.count(), 10)
        self.assertEqual(Expense.objects.count(), 3)
        self.assertTrue(PaymentAllocation.objects.filter(receipt__receipt_number='REC-00001').exists())
        self.assertGreaterEqual(StatementRun.objects.count(), 1)

    def test_receipt_allocation_update_view(self):
        second_invoice = Invoice.objects.create(
            invoice_number='INV-00002',
            customer=self.customer,
            created_by=self.user,
            status='sent',
            invoice_date=date.today() - timedelta(days=5),
            due_date=date.today() + timedelta(days=10),
            tax_rate=Decimal('0.00'),
            subtotal=Decimal('300.00'),
            total_amount=Decimal('300.00'),
            paid_amount=Decimal('0.00'),
        )

        receipt = Receipt.objects.get(receipt_number='REC-00001')
        response = self.client.post(
            reverse('finance:receipt-allocation-update', args=[receipt.pk]),
            {
                f'alloc_{self.invoice.pk}': '100.00',
                f'alloc_{second_invoice.pk}': '150.00',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PaymentAllocation.objects.filter(receipt=receipt).count(), 2)

    def test_profit_loss_view_renders(self):
        response = self.client.get(reverse('finance:profit-loss'), {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profit & Loss')

    def test_generate_monthly_statements_command(self):
        output = StringIO()
        call_command('generate_monthly_statements', stdout=output)
        self.assertGreaterEqual(StatementRun.objects.count(), 1)
