from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    company = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    def get_absolute_url(self):
        return reverse('customer-detail', kwargs={'pk': self.pk})

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    quotation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotations')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    quotation_date = models.DateField()
    valid_until = models.DateField()
    
    # Event Details
    event_start_date = models.DateField(null=True, blank=True, verbose_name='Event Start Date')
    event_end_date = models.DateField(null=True, blank=True, verbose_name='Event End Date')
    event_location = models.CharField(max_length=500, blank=True, verbose_name='Event Location')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-quotation_date']
    
    def __str__(self):
        return f"Quotation {self.quotation_number} - {self.customer.name}"
    
    def get_absolute_url(self):
        return reverse('quotation-detail', kwargs={'pk': self.pk})
    
    def calculate_totals(self):
        self.subtotal = sum(item.line_total for item in self.items.all())
        # Only recalculate discount_amount if discount_percentage is set
        # If discount_amount is manually set (fixed amount), preserve it
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        # If discount_amount is set but percentage is 0, calculate percentage from amount
        elif self.discount_amount > 0 and self.subtotal > 0:
            self.discount_percentage = (self.discount_amount / self.subtotal) * 100
        discounted_subtotal = self.subtotal - self.discount_amount
        self.tax_amount = discounted_subtotal * (self.tax_rate / 100)
        self.total_amount = discounted_subtotal + self.tax_amount
        self.save()

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    invoice_date = models.DateField()
    due_date = models.DateField()
    
    # Event Details
    event_start_date = models.DateField(null=True, blank=True, verbose_name='Event Start Date')
    event_end_date = models.DateField(null=True, blank=True, verbose_name='Event End Date')
    event_location = models.CharField(max_length=500, blank=True, verbose_name='Event Location')
    
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"
    
    def get_absolute_url(self):
        return reverse('invoice-detail', kwargs={'pk': self.pk})
    
    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount
    
    def calculate_totals(self):
        self.subtotal = sum(item.line_total for item in self.items.all())
        # Only recalculate discount_amount if discount_percentage is set
        # If discount_amount is manually set (fixed amount), preserve it
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        # If discount_amount is set but percentage is 0, calculate percentage from amount
        elif self.discount_amount > 0 and self.subtotal > 0:
            self.discount_percentage = (self.discount_amount / self.subtotal) * 100
        discounted_subtotal = self.subtotal - self.discount_amount
        self.tax_amount = discounted_subtotal * (self.tax_rate / 100)
        self.total_amount = discounted_subtotal + self.tax_amount
        self.save()

class Receipt(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
    ]
    
    receipt_number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='receipts')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.customer.name} - ${self.amount}"
    
    def get_absolute_url(self):
        return reverse('receipt-detail', kwargs={'pk': self.pk})

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.description} - {self.quotation.quotation_number}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.description} - {self.invoice.invoice_number}"
