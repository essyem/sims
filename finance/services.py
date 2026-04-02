from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from sales.models import Customer, Invoice

from .models import PaymentAllocation, StatementRun


ZERO = Decimal('0.00')


def _sum_amount(queryset, field_name):
    value = queryset.aggregate(total=Sum(field_name))['total']
    return value or ZERO


def recalculate_invoice_paid_amount(invoice):
    allocation_total = PaymentAllocation.objects.filter(invoice=invoice).aggregate(total=Sum('amount'))['total'] or ZERO
    # Backward-compatible path for receipts that don't have allocations yet.
    legacy_total = invoice.receipts.filter(allocations__isnull=True).aggregate(total=Sum('amount'))['total'] or ZERO
    paid_amount = allocation_total + legacy_total

    invoice.paid_amount = paid_amount
    if paid_amount >= invoice.total_amount:
        invoice.status = 'paid'
    elif invoice.due_date < timezone.localdate() and paid_amount < invoice.total_amount:
        invoice.status = 'overdue'
    elif paid_amount > ZERO and invoice.status == 'draft':
        invoice.status = 'sent'
    elif paid_amount == ZERO and invoice.status == 'paid':
        invoice.status = 'sent'
    invoice.save(update_fields=['paid_amount', 'status', 'updated_at'])
    return invoice


def recalculate_customer_invoices(customer):
    invoices = Invoice.objects.filter(customer=customer)
    for invoice in invoices:
        recalculate_invoice_paid_amount(invoice)
    return invoices


def ensure_receipt_default_allocation(receipt):
    if receipt.allocations.exists():
        return
    PaymentAllocation.objects.create(
        receipt=receipt,
        invoice=receipt.invoice,
        amount=receipt.amount,
    )


def apply_receipt_allocation_map(receipt, allocation_map):
    PaymentAllocation.objects.filter(receipt=receipt).delete()
    total = ZERO
    for invoice, amount in allocation_map:
        if amount <= ZERO:
            continue
        PaymentAllocation.objects.create(receipt=receipt, invoice=invoice, amount=amount)
        total += amount

    # Keep any remainder on the originally linked invoice for backwards compatibility.
    remainder = receipt.amount - total
    if remainder > ZERO:
        existing = PaymentAllocation.objects.filter(receipt=receipt, invoice=receipt.invoice).first()
        if existing:
            existing.amount += remainder
            existing.save(update_fields=['amount', 'updated_at'])
        else:
            PaymentAllocation.objects.create(receipt=receipt, invoice=receipt.invoice, amount=remainder)

    impacted_invoice_ids = set(PaymentAllocation.objects.filter(receipt=receipt).values_list('invoice_id', flat=True))
    impacted_invoice_ids.add(receipt.invoice_id)
    for invoice in Invoice.objects.filter(id__in=impacted_invoice_ids):
        recalculate_invoice_paid_amount(invoice)


def generate_statement_runs(period_start, period_end, generated_by=None, customer=None):
    customers = Customer.objects.all()
    if customer is not None:
        customers = customers.filter(pk=customer.pk)

    runs = []
    for candidate in customers:
        statement = build_customer_statement(candidate, start_date=period_start, end_date=period_end)
        if statement['period_debits'] == ZERO and statement['period_credits'] == ZERO and statement['closing_balance'] == ZERO:
            continue
        run = StatementRun.objects.create(
            customer=candidate,
            period_start=period_start,
            period_end=period_end,
            opening_balance=statement['opening_balance'],
            total_debits=statement['period_debits'],
            total_credits=statement['period_credits'],
            closing_balance=statement['closing_balance'],
            generated_by=generated_by,
            status='generated',
        )
        runs.append(run)
    return runs


def build_customer_statement(customer, start_date=None, end_date=None):
    if not isinstance(customer, Customer):
        customer = Customer.objects.get(pk=customer)

    invoices = customer.invoices.all().order_by('invoice_date', 'id')
    receipts = customer.receipts.all().order_by('payment_date', 'id')

    if end_date:
        invoices = invoices.filter(invoice_date__lte=end_date)
        receipts = receipts.filter(payment_date__lte=end_date)

    opening_invoices = invoices.none()
    opening_receipts = receipts.none()
    period_invoices = invoices
    period_receipts = receipts

    if start_date:
        opening_invoices = invoices.filter(invoice_date__lt=start_date)
        opening_receipts = receipts.filter(payment_date__lt=start_date)
        period_invoices = invoices.filter(invoice_date__gte=start_date)
        period_receipts = receipts.filter(payment_date__gte=start_date)

    opening_balance = _sum_amount(opening_invoices, 'total_amount') - _sum_amount(opening_receipts, 'amount')

    entries = []
    running_balance = opening_balance

    for invoice in period_invoices:
        running_balance += invoice.total_amount
        entries.append({
            'date': invoice.invoice_date,
            'entry_type': 'invoice',
            'reference': invoice.invoice_number,
            'description': f'Invoice issued ({invoice.get_status_display()})',
            'debit': invoice.total_amount,
            'credit': ZERO,
            'balance': running_balance,
            'url': reverse('invoice-detail', kwargs={'pk': invoice.pk}),
        })

    for receipt in period_receipts:
        allocated_amount = receipt.allocations.aggregate(total=Sum('amount'))['total']
        credit_amount = allocated_amount if allocated_amount is not None else receipt.amount
        running_balance -= credit_amount
        entries.append({
            'date': receipt.payment_date,
            'entry_type': 'receipt',
            'reference': receipt.receipt_number,
            'description': f'Receipt posted via {receipt.get_payment_method_display()}',
            'debit': ZERO,
            'credit': credit_amount,
            'balance': running_balance,
            'url': reverse('receipt-detail', kwargs={'pk': receipt.pk}),
        })

    entries.sort(key=lambda entry: (entry['date'], 0 if entry['entry_type'] == 'invoice' else 1, entry['reference']))

    running_balance = opening_balance
    for entry in entries:
        running_balance += entry['debit']
        running_balance -= entry['credit']
        entry['balance'] = running_balance

    outstanding_invoices = customer.invoices.filter(total_amount__gt=models.F('paid_amount')).order_by('due_date', 'invoice_date')
    today = timezone.localdate()

    aging = {
        'current': ZERO,
        'days_1_30': ZERO,
        'days_31_60': ZERO,
        'days_61_90': ZERO,
        'days_90_plus': ZERO,
    }

    for invoice in outstanding_invoices:
        balance_due = invoice.balance_due
        if balance_due <= 0:
            continue
        days_overdue = (today - invoice.due_date).days
        if days_overdue <= 0:
            aging['current'] += balance_due
        elif days_overdue <= 30:
            aging['days_1_30'] += balance_due
        elif days_overdue <= 60:
            aging['days_31_60'] += balance_due
        elif days_overdue <= 90:
            aging['days_61_90'] += balance_due
        else:
            aging['days_90_plus'] += balance_due

    return {
        'customer': customer,
        'start_date': start_date,
        'end_date': end_date,
        'opening_balance': opening_balance,
        'entries': entries,
        'period_debits': sum((entry['debit'] for entry in entries), ZERO),
        'period_credits': sum((entry['credit'] for entry in entries), ZERO),
        'closing_balance': running_balance,
        'outstanding_invoices': outstanding_invoices,
        'aging': aging,
    }
