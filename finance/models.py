from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from sales.models import Customer, Invoice, Receipt


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'expense categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]

    expense_number = models.CharField(max_length=50, unique=True, blank=True)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField()
    vendor = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.expense_number} - {self.title}"

    def get_absolute_url(self):
        return reverse('finance:expense-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.expense_number:
            last_expense = Expense.objects.order_by('-id').first()
            next_number = (last_expense.id + 1) if last_expense else 1
            self.expense_number = f"EXP-{next_number:05d}"
        super().save(*args, **kwargs)


class PaymentAllocation(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['invoice__due_date', 'invoice__invoice_date']
        unique_together = ('receipt', 'invoice')

    def __str__(self):
        return f"{self.receipt.receipt_number} -> {self.invoice.invoice_number} ({self.amount})"


class StatementRun(models.Model):
    STATUS_CHOICES = [
        ('generated', 'Generated'),
        ('emailed', 'Emailed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='statement_runs')
    period_start = models.DateField()
    period_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_debits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    emailed_to = models.EmailField(blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', '-created_at']

    def __str__(self):
        return f"Statement {self.customer.name}: {self.period_start} to {self.period_end}"
