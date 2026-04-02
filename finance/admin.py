from django.contrib import admin

from .models import Expense, ExpenseCategory, PaymentAllocation, StatementRun


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_number', 'title', 'category', 'amount', 'expense_date', 'payment_method')
    list_filter = ('payment_method', 'category', 'expense_date')
    search_fields = ('expense_number', 'title', 'vendor', 'reference_number')


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('receipt', 'invoice', 'amount', 'updated_at')
    search_fields = ('receipt__receipt_number', 'invoice__invoice_number', 'invoice__customer__name')
    list_filter = ('updated_at',)


@admin.register(StatementRun)
class StatementRunAdmin(admin.ModelAdmin):
    list_display = ('customer', 'period_start', 'period_end', 'closing_balance', 'status', 'emailed_at')
    search_fields = ('customer__name', 'customer__email')
    list_filter = ('status', 'period_start', 'period_end')
