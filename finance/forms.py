from django import forms

from sales.models import Invoice

from .models import Expense, StatementRun


class DateInput(forms.DateInput):
    input_type = 'date'


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'title',
            'category',
            'amount',
            'expense_date',
            'vendor',
            'payment_method',
            'reference_number',
            'notes',
        ]
        widgets = {
            'expense_date': DateInput(),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class StatementRunEmailForm(forms.ModelForm):
    class Meta:
        model = StatementRun
        fields = ['emailed_to']
        widgets = {
            'emailed_to': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@example.com'})
        }


class ReceiptAllocationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        outstanding_invoices = kwargs.pop('outstanding_invoices')
        existing_allocations = kwargs.pop('existing_allocations')
        super().__init__(*args, **kwargs)

        for invoice in outstanding_invoices:
            field_name = f'alloc_{invoice.pk}'
            initial_value = existing_allocations.get(invoice.pk, 0)
            self.fields[field_name] = forms.DecimalField(
                required=False,
                min_value=0,
                decimal_places=2,
                max_digits=10,
                initial=initial_value,
                label=f'{invoice.invoice_number} ({invoice.invoice_date})',
                widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
            )


class ProfitLossFilterForm(forms.Form):
    start_date = forms.DateField(widget=DateInput(), required=True)
    end_date = forms.DateField(widget=DateInput(), required=True)


class InvoiceAllocationChoiceForm(forms.Form):
    invoice = forms.ModelChoiceField(queryset=Invoice.objects.none(), required=True)
    amount = forms.DecimalField(min_value=0, decimal_places=2, max_digits=10)

    def __init__(self, *args, **kwargs):
        invoices = kwargs.pop('invoices')
        super().__init__(*args, **kwargs)
        self.fields['invoice'].queryset = invoices
