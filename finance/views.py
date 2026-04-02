from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from sales.models import Customer, Invoice, Receipt

from .forms import ExpenseForm, ProfitLossFilterForm, ReceiptAllocationForm
from .models import Expense, StatementRun
from .services import (
    apply_receipt_allocation_map,
    build_customer_statement,
    generate_statement_runs,
)


def _previous_month(month_start):
    return (month_start - timedelta(days=1)).replace(day=1)


def _end_of_month(any_day):
    return (any_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _statement_filters(request, kwargs):
    customer_id = request.GET.get('customer') or kwargs.get('customer_id')
    start_date_raw = request.GET.get('start_date') or None
    end_date_raw = request.GET.get('end_date') or None
    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None
    return customer_id, start_date_raw, end_date_raw, start_date, end_date


class FinanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        month_cursor = today.replace(day=1)
        monthly_data = []
        for _ in range(6):
            next_month = (month_cursor + timedelta(days=32)).replace(day=1)
            invoiced = Invoice.objects.filter(invoice_date__gte=month_cursor, invoice_date__lt=next_month).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            collected = Receipt.objects.filter(payment_date__gte=month_cursor, payment_date__lt=next_month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            expenses = Expense.objects.filter(expense_date__gte=month_cursor, expense_date__lt=next_month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            monthly_data.append({
                'label': month_cursor.strftime('%b %Y'),
                'invoiced': float(invoiced),
                'collected': float(collected),
                'expenses': float(expenses),
                'net': float(collected - expenses),
            })
            month_cursor = _previous_month(month_cursor)

        monthly_data.reverse()
        total_invoiced = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = Receipt.objects.aggregate(total=Sum('amount'))['total'] or 0
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        this_month = date.today().replace(day=1)

        context.update({
            'total_invoiced': total_invoiced,
            'total_collected': total_paid,
            'total_expenses': total_expenses,
            'net_cash_position': total_paid - total_expenses,
            'outstanding_receivables': total_invoiced - (Invoice.objects.aggregate(total=Sum('paid_amount'))['total'] or 0),
            'this_month_expenses': Expense.objects.filter(expense_date__gte=this_month).aggregate(total=Sum('amount'))['total'] or 0,
            'recent_expenses': Expense.objects.select_related('category').order_by('-expense_date', '-created_at')[:8],
            'monthly_data': monthly_data,
            'monthly_chart_labels': [item['label'] for item in monthly_data],
            'monthly_chart_invoiced': [item['invoiced'] for item in monthly_data],
            'monthly_chart_collected': [item['collected'] for item in monthly_data],
            'monthly_chart_expenses': [item['expenses'] for item in monthly_data],
            'top_customers': sorted(
                [
                    {
                        'customer': customer,
                        'outstanding': sum((invoice.balance_due for invoice in customer.invoices.all()), Decimal('0.00')),
                    }
                    for customer in Customer.objects.all()
                ],
                key=lambda item: item['outstanding'],
                reverse=True,
            )[:5],
            'recent_statement_runs': StatementRun.objects.select_related('customer').order_by('-created_at')[:6],
        })
        return context


class CustomerStatementView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/statement/customer_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id, start_date_raw, end_date_raw, start_date, end_date = _statement_filters(self.request, self.kwargs)

        statement = None
        selected_customer = None

        if customer_id:
            selected_customer = get_object_or_404(Customer, pk=customer_id)
            statement = build_customer_statement(selected_customer, start_date=start_date, end_date=end_date)

        context.update({
            'customers': Customer.objects.order_by('name'),
            'selected_customer': selected_customer,
            'statement': statement,
            'selected_start_date': start_date_raw,
            'selected_end_date': end_date_raw,
        })
        return context


class CustomerStatementPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        customer_id, start_date_raw, end_date_raw, start_date, end_date = _statement_filters(request, kwargs)
        customer = get_object_or_404(Customer, pk=customer_id)
        statement = build_customer_statement(customer, start_date=start_date, end_date=end_date)
        html_content = render_to_string(
            'finance/statement/customer_statement_pdf.html',
            {
                'statement': statement,
                'selected_start_date': start_date_raw,
                'selected_end_date': end_date_raw,
            },
            request=request,
        )

        import weasyprint

        html_doc = weasyprint.HTML(string=html_content, base_url=request.build_absolute_uri('/'))
        pdf_file = html_doc.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="statement_{customer.pk}.pdf"'
        return response


class ReceiptAllocationUpdateView(LoginRequiredMixin, View):
    template_name = 'finance/receipt_allocation_form.html'

    def _build_context(self, receipt, form):
        allocations = receipt.allocations.select_related('invoice').order_by('invoice__due_date', 'invoice__invoice_date')
        allocated_total = allocations.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        invoice_rows = []
        for invoice in receipt.customer.invoices.order_by('due_date', 'invoice_date', 'id'):
            field_name = f'alloc_{invoice.pk}'
            if field_name in form.fields:
                invoice_rows.append({'invoice': invoice, 'field': form[field_name]})
        return {
            'receipt': receipt,
            'form': form,
            'allocations': allocations,
            'invoice_rows': invoice_rows,
            'allocated_total': allocated_total,
            'unallocated_total': receipt.amount - allocated_total,
        }

    def get(self, request, receipt_id):
        receipt = get_object_or_404(Receipt, pk=receipt_id)
        invoices = receipt.customer.invoices.order_by('due_date', 'invoice_date', 'id')
        existing_allocations = {item.invoice_id: item.amount for item in receipt.allocations.all()}
        form = ReceiptAllocationForm(outstanding_invoices=invoices, existing_allocations=existing_allocations)
        return render(request, self.template_name, self._build_context(receipt, form))

    def post(self, request, receipt_id):
        receipt = get_object_or_404(Receipt, pk=receipt_id)
        invoices = receipt.customer.invoices.order_by('due_date', 'invoice_date', 'id')
        existing_allocations = {item.invoice_id: item.amount for item in receipt.allocations.all()}
        form = ReceiptAllocationForm(request.POST, outstanding_invoices=invoices, existing_allocations=existing_allocations)

        if not form.is_valid():
            return render(request, self.template_name, self._build_context(receipt, form))

        allocation_map = []
        total = Decimal('0.00')
        for invoice in invoices:
            amount = form.cleaned_data.get(f'alloc_{invoice.pk}') or Decimal('0.00')
            amount = amount.quantize(Decimal('0.01'))
            if amount > Decimal('0.00'):
                allocation_map.append((invoice, amount))
                total += amount

        if total > receipt.amount:
            form.add_error(None, f'Allocated total {total} exceeds receipt amount {receipt.amount}.')
            return render(request, self.template_name, self._build_context(receipt, form))

        apply_receipt_allocation_map(receipt, allocation_map)
        messages.success(request, 'Receipt allocations updated successfully.')
        return redirect('receipt-detail', pk=receipt.pk)


class StatementRunListView(LoginRequiredMixin, ListView):
    model = StatementRun
    template_name = 'finance/run_list.html'
    context_object_name = 'runs'
    paginate_by = 30

    def get_queryset(self):
        queryset = StatementRun.objects.select_related('customer', 'generated_by')
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        previous_month_start = _previous_month(today.replace(day=1))
        context['customers'] = Customer.objects.order_by('name')
        context['default_start'] = previous_month_start
        context['default_end'] = _end_of_month(previous_month_start)
        return context


class GenerateStatementRunsView(LoginRequiredMixin, View):
    def post(self, request):
        start_date = parse_date(request.POST.get('period_start'))
        end_date = parse_date(request.POST.get('period_end'))
        customer_id = request.POST.get('customer')

        if not start_date or not end_date or start_date > end_date:
            messages.error(request, 'Please provide a valid statement period.')
            return redirect('finance:statement-run-list')

        customer = None
        if customer_id:
            customer = get_object_or_404(Customer, pk=customer_id)

        runs = generate_statement_runs(start_date, end_date, generated_by=request.user, customer=customer)
        messages.success(request, f'Generated {len(runs)} statement run record(s).')
        return redirect('finance:statement-run-list')


class MarkStatementEmailedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        run = get_object_or_404(StatementRun, pk=pk)
        email = request.POST.get('emailed_to') or run.customer.email
        run.emailed_to = email or ''
        run.status = 'emailed'
        run.emailed_at = timezone.now()
        run.save(update_fields=['emailed_to', 'status', 'emailed_at', 'updated_at'])
        messages.success(request, 'Statement marked as emailed.')
        return redirect('finance:statement-run-list')


class ProfitLossView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/profit_loss.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        default_start = today.replace(day=1)
        default_end = today

        form = ProfitLossFilterForm(self.request.GET or None, initial={'start_date': default_start, 'end_date': default_end})
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date, end_date = default_start, default_end

        invoiced = Invoice.objects.filter(invoice_date__range=[start_date, end_date]).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        collected = Receipt.objects.filter(payment_date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        expenses = Expense.objects.filter(expense_date__range=[start_date, end_date]).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        category_breakdown = (
            Expense.objects.filter(expense_date__range=[start_date, end_date])
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        context.update({
            'form': form,
            'period_start': start_date,
            'period_end': end_date,
            'invoiced_revenue': invoiced,
            'collected_revenue': collected,
            'total_expenses': expenses,
            'net_profit_cash_basis': collected - expenses,
            'net_profit_accrual_basis': invoiced - expenses,
            'category_breakdown': category_breakdown,
        })
        return context


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'finance/expense/list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        queryset = Expense.objects.select_related('category', 'created_by')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    model = Expense
    template_name = 'finance/expense/detail.html'
    context_object_name = 'expense'


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense/form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Expense created successfully.')
        return super().form_valid(form)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense/form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully.')
        return super().form_valid(form)


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'finance/expense/confirm_delete.html'
    success_url = reverse_lazy('finance:expense-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense deleted successfully.')
        return super().delete(request, *args, **kwargs)
