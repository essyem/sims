from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q
from sales.models import Customer, Invoice, Receipt
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Show receivables and analytics report'

    def handle(self, *args, **options):
        today = date.today()
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('📊 RECEIVABLES & ANALYTICS REPORT'))
        self.stdout.write('='*60)
        
        # Overall financial summary
        total_invoices = Invoice.objects.count()
        total_amount = Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        total_paid = Invoice.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
        total_outstanding = total_amount - total_paid
        
        self.stdout.write(f'💰 FINANCIAL OVERVIEW:')
        self.stdout.write(f'   Total Invoices: {total_invoices}')
        self.stdout.write(f'   Total Invoiced: {total_amount:,.2f} QAR')
        self.stdout.write(f'   Total Collected: {total_paid:,.2f} QAR')
        self.stdout.write(f'   Outstanding: {total_outstanding:,.2f} QAR')
        self.stdout.write(f'   Collection Rate: {(total_paid/total_amount*100 if total_amount > 0 else 0):.1f}%')
        self.stdout.write('')
        
        # Aging analysis\n        overdue_30 = Invoice.objects.filter(\n            due_date__lt=today - timedelta(days=30),\n            status__in=['sent', 'overdue']\n        ).aggregate(Sum('total_amount'), Count('id'))\n        \n        overdue_60 = Invoice.objects.filter(\n            due_date__lt=today - timedelta(days=60),\n            status__in=['sent', 'overdue']\n        ).aggregate(Sum('total_amount'), Count('id'))\n        \n        overdue_90 = Invoice.objects.filter(\n            due_date__lt=today - timedelta(days=90),\n            status__in=['sent', 'overdue']\n        ).aggregate(Sum('total_amount'), Count('id'))\n        \n        current = Invoice.objects.filter(\n            due_date__gte=today,\n            status__in=['sent', 'overdue']\n        ).aggregate(Sum('total_amount'), Count('id'))\n        \n        self.stdout.write(f'📅 AGING ANALYSIS:')\n        self.stdout.write(f'   Current (Not Due): {current[\"id__count\"] or 0} invoices, {current[\"total_amount__sum\"] or 0:,.2f} QAR')\n        self.stdout.write(f'   1-30 days overdue: {overdue_30[\"id__count\"] or 0} invoices, {overdue_30[\"total_amount__sum\"] or 0:,.2f} QAR')\n        self.stdout.write(f'   31-60 days overdue: {overdue_60[\"id__count\"] or 0} invoices, {overdue_60[\"total_amount__sum\"] or 0:,.2f} QAR')\n        self.stdout.write(f'   60+ days overdue: {overdue_90[\"id__count\"] or 0} invoices, {overdue_90[\"total_amount__sum\"] or 0:,.2f} QAR')\n        self.stdout.write('')\n        \n        # Top customers by outstanding balance\n        self.stdout.write(f'🏆 TOP 10 CUSTOMERS BY OUTSTANDING BALANCE:')\n        customers_with_balance = []\n        \n        for customer in Customer.objects.all():\n            invoices = customer.invoices.all()\n            total_owed = sum((inv.total_amount - inv.paid_amount) for inv in invoices)\n            if total_owed > 0:\n                customers_with_balance.append((customer, total_owed, invoices.count()))\n        \n        customers_with_balance.sort(key=lambda x: x[1], reverse=True)\n        \n        for i, (customer, balance, invoice_count) in enumerate(customers_with_balance[:10]):\n            self.stdout.write(f'   {i+1:2d}. {customer.name[:30]:<30} {balance:>10,.2f} QAR ({invoice_count} invoices)')\n        \n        self.stdout.write('')\n        \n        # Payment method analysis\n        self.stdout.write(f'💳 PAYMENT METHOD ANALYSIS:')\n        payment_methods = Receipt.objects.values('payment_method').annotate(\n            total_amount=Sum('amount'),\n            count=Count('id')\n        ).order_by('-total_amount')\n        \n        for method in payment_methods:\n            method_display = dict(Receipt.PAYMENT_METHOD_CHOICES).get(method['payment_method'], method['payment_method'])\n            self.stdout.write(f'   {method_display}: {method[\"total_amount\"]:,.2f} QAR ({method[\"count\"]} transactions)')\n        \n        self.stdout.write('')\n        \n        # Recent activity\n        recent_invoices = Invoice.objects.filter(\n            created_at__gte=today - timedelta(days=30)\n        ).count()\n        \n        recent_payments = Receipt.objects.filter(\n            created_at__gte=today - timedelta(days=30)\n        ).count()\n        \n        self.stdout.write(f'📈 RECENT ACTIVITY (Last 30 days):')\n        self.stdout.write(f'   New Invoices: {recent_invoices}')\n        self.stdout.write(f'   Payments Received: {recent_payments}')\n        \n        self.stdout.write('')\n        self.stdout.write('='*60)\n        self.stdout.write(self.style.SUCCESS('📊 Report Complete - Visit http://localhost:8010/ for detailed views'))\n        self.stdout.write('='*60)