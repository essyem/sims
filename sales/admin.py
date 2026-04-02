from django.contrib import admin
from .models import Customer, Invoice, Quotation, Receipt, InvoiceItem, QuotationItem

def format_qar_currency(amount):
    """Format amount with QAR currency"""
    if amount is None:
        return "0.00 QAR"
    return f"{amount:.2f} QAR"

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ['line_total_qar']
    
    def line_total_qar(self, obj):
        if obj.line_total:
            return format_qar_currency(obj.line_total)
        return "0.00 QAR"
    line_total_qar.short_description = 'Line Total (QAR)'

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    readonly_fields = ['line_total_qar']
    
    def line_total_qar(self, obj):
        if obj.line_total:
            return format_qar_currency(obj.line_total)
        return "0.00 QAR"
    line_total_qar.short_description = 'Line Total (QAR)'

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'company', 'created_at']
    list_filter = ['created_at', 'company']
    search_fields = ['name', 'phone', 'email', 'company']
    ordering = ['name']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['quotation_number', 'customer', 'status', 'quotation_date', 'total_amount_qar', 'created_by']
    list_filter = ['status', 'quotation_date', 'created_at']
    search_fields = ['quotation_number', 'customer__name', 'customer__email']
    readonly_fields = ['quotation_number', 'subtotal_qar', 'tax_amount_qar', 'total_amount_qar']
    inlines = [QuotationItemInline]
    
    def total_amount_qar(self, obj):
        return format_qar_currency(obj.total_amount)
    total_amount_qar.short_description = 'Total Amount'
    total_amount_qar.admin_order_field = 'total_amount'
    
    def subtotal_qar(self, obj):
        return format_qar_currency(obj.subtotal)
    subtotal_qar.short_description = 'Subtotal (QAR)'
    
    def tax_amount_qar(self, obj):
        return format_qar_currency(obj.tax_amount)
    tax_amount_qar.short_description = 'Tax Amount (QAR)'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'status', 'invoice_date', 'total_amount_qar', 'balance_due_qar', 'created_by']
    list_filter = ['status', 'invoice_date', 'created_at']
    search_fields = ['invoice_number', 'customer__name', 'customer__email']
    readonly_fields = ['invoice_number', 'subtotal_qar', 'tax_amount_qar', 'total_amount_qar', 'balance_due_qar']
    inlines = [InvoiceItemInline]
    
    def total_amount_qar(self, obj):
        return format_qar_currency(obj.total_amount)
    total_amount_qar.short_description = 'Total Amount'
    total_amount_qar.admin_order_field = 'total_amount'
    
    def balance_due_qar(self, obj):
        return format_qar_currency(obj.balance_due)
    balance_due_qar.short_description = 'Balance Due'
    balance_due_qar.admin_order_field = 'total_amount'
    
    def subtotal_qar(self, obj):
        return format_qar_currency(obj.subtotal)
    subtotal_qar.short_description = 'Subtotal (QAR)'
    
    def tax_amount_qar(self, obj):
        return format_qar_currency(obj.tax_amount)
    tax_amount_qar.short_description = 'Tax Amount (QAR)'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'customer', 'invoice', 'amount_qar', 'payment_method', 'payment_date', 'created_by']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = ['receipt_number', 'customer__name', 'invoice__invoice_number']
    readonly_fields = ['receipt_number']
    
    def amount_qar(self, obj):
        return format_qar_currency(obj.amount)
    amount_qar.short_description = 'Amount'
    amount_qar.admin_order_field = 'amount'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'description', 'quantity', 'unit_price_qar', 'line_total_qar']
    list_filter = ['invoice__invoice_date']
    search_fields = ['description', 'invoice__invoice_number']
    
    def unit_price_qar(self, obj):
        return format_qar_currency(obj.unit_price)
    unit_price_qar.short_description = 'Unit Price'
    unit_price_qar.admin_order_field = 'unit_price'
    
    def line_total_qar(self, obj):
        return format_qar_currency(obj.line_total)
    line_total_qar.short_description = 'Line Total'
    line_total_qar.admin_order_field = 'line_total'

@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
    list_display = ['quotation', 'description', 'quantity', 'unit_price_qar', 'line_total_qar']
    list_filter = ['quotation__quotation_date']
    search_fields = ['description', 'quotation__quotation_number']
    
    def unit_price_qar(self, obj):
        return format_qar_currency(obj.unit_price)
    unit_price_qar.short_description = 'Unit Price'
    unit_price_qar.admin_order_field = 'unit_price'
    
    def line_total_qar(self, obj):
        return format_qar_currency(obj.line_total)
    line_total_qar.short_description = 'Line Total'
    line_total_qar.admin_order_field = 'line_total'
