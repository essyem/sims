from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, F, Count, Avg
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django import forms
from .models import Customer, Invoice, Quotation, Receipt, InvoiceItem, QuotationItem
from .forms import CustomerForm, InvoiceForm, QuotationForm, ReceiptForm
import json
from datetime import datetime, date
from decimal import Decimal

# Dashboard View
@login_required
def dashboard(request):
    from django.db.models import Sum
    from datetime import date, timedelta
    
    today = date.today()
    
    # Financial calculations
    total_invoiced = Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = Invoice.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_outstanding = total_invoiced - total_paid
    
    # Overdue analysis
    overdue_30_days = Invoice.objects.filter(
        due_date__lt=today - timedelta(days=30),
        status__in=['sent', 'overdue']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'total_customers': Customer.objects.count(),
        'total_invoices': Invoice.objects.count(),
        'total_quotations': Quotation.objects.count(),
        'total_receipts': Receipt.objects.count(),
        'pending_invoices': Invoice.objects.filter(status='sent').count(),
        'overdue_invoices': Invoice.objects.filter(status='overdue').count(),
        'recent_invoices': Invoice.objects.order_by('-created_at')[:5],
        'recent_quotations': Quotation.objects.order_by('-created_at')[:5],
        
        # Financial metrics
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
        'overdue_30_days': overdue_30_days,
        'collection_rate': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0,
        
        # Top customers with outstanding balances
        'top_outstanding_customers': get_top_outstanding_customers()[:5],
    }
    return render(request, 'sales/dashboard.html', context)

def get_top_outstanding_customers():
    """Get customers with highest outstanding balances"""
    customers_with_balance = []
    
    for customer in Customer.objects.all():
        invoices = customer.invoices.all()
        total_owed = sum((inv.total_amount - inv.paid_amount) for inv in invoices if (inv.total_amount - inv.paid_amount) > 0)
        if total_owed > 0:
            customers_with_balance.append({
                'customer': customer,
                'outstanding_balance': total_owed,
                'invoice_count': invoices.filter(total_amount__gt=F('paid_amount')).count()
            })
    
    return sorted(customers_with_balance, key=lambda x: x['outstanding_balance'], reverse=True)

# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'sales/customer/list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        return queryset

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'sales/customer/detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        context['invoices'] = customer.invoices.order_by('-invoice_date')[:10]
        context['quotations'] = customer.quotations.order_by('-quotation_date')[:10]
        context['receipts'] = customer.receipts.order_by('-payment_date')[:10]
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = 'sales/customer/form.html'
    fields = ['name', 'phone', 'email', 'address', 'company']
    
    def form_valid(self, form):
        customer = form.save()
        
        # Handle AJAX requests
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'customer': {
                    'id': customer.id,
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone or '',
                    'company': customer.company or '',
                    'address': customer.address or ''
                }
            })
        
        messages.success(self.request, 'Customer created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Handle AJAX requests for form errors
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Create a more detailed error message
            error_details = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_details.append(f"{field}: {error}")
            
            error_message = "Form validation failed: " + "; ".join(error_details) if error_details else "Please check the form for errors."
            
            return JsonResponse({
                'success': False,
                'error': error_message,
                'errors': form.errors
            })
        
        return super().form_invalid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = 'sales/customer/form.html'
    fields = ['name', 'phone', 'email', 'address', 'company']
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'sales/customer/confirm_delete.html'
    success_url = reverse_lazy('customer-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Customer deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Quotation Views
class QuotationListView(LoginRequiredMixin, ListView):
    model = Quotation
    template_name = 'sales/quotation/list.html'
    context_object_name = 'quotations'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Quotation.objects.select_related('customer', 'created_by')
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(quotation_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

class QuotationDetailView(LoginRequiredMixin, DetailView):
    model = Quotation
    template_name = 'sales/quotation/detail.html'
    context_object_name = 'quotation'

class QuotationCreateView(LoginRequiredMixin, CreateView):
    model = Quotation
    template_name = 'sales/quotation/form.html'
    fields = ['customer', 'quotation_date', 'valid_until', 'status', 'event_start_date', 'event_end_date', 'event_location', 'tax_rate', 'discount_percentage', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        
        # Get recent items for suggestions
        recent_items = QuotationItem.objects.values('description', 'unit_price').annotate(
            count=Count('id')
        ).order_by('-count')[:20]
        
        # Convert to JSON for JavaScript
        existing_items = []
        for item in recent_items:
            existing_items.append({
                'description': item['description'],
                'unit_price': float(item['unit_price'])
            })
        
        context['existing_items'] = json.dumps(existing_items)
        context['today'] = datetime.now().date().isoformat()
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Auto-generate quotation number
        last_quotation = Quotation.objects.order_by('-id').first()
        if last_quotation:
            next_number = int(last_quotation.quotation_number.split('-')[-1]) + 1
        else:
            next_number = 1
        form.instance.quotation_number = f"QT-{next_number:05d}"
        
        # Handle empty discount/tax values
        if not form.instance.discount_percentage:
            form.instance.discount_percentage = Decimal('0.00')
        if not form.instance.tax_rate:
            form.instance.tax_rate = Decimal('0.00')
        
        # Handle fixed discount amount if provided
        discount_amount_input = self.request.POST.get('discount_amount_input', '0.00')
        if discount_amount_input and Decimal(discount_amount_input) > 0:
            form.instance.discount_amount = Decimal(discount_amount_input)
            # Don't override percentage if user set fixed amount
            form.instance.discount_percentage = Decimal('0.00')
        
        # Save the quotation first
        response = super().form_valid(form)
        quotation = form.instance
        
        # Process items data
        item_index = 0
        while f'items-{item_index}-description' in self.request.POST:
            description = self.request.POST.get(f'items-{item_index}-description')
            quantity = self.request.POST.get(f'items-{item_index}-quantity')
            unit_price = self.request.POST.get(f'items-{item_index}-unit_price')
            
            if description and quantity and unit_price:
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=description,
                    quantity=Decimal(quantity),
                    unit_price=Decimal(unit_price)
                )
            item_index += 1
        
        # Calculate totals
        quotation.calculate_totals()
        
        messages.success(self.request, 'Quotation created successfully!')
        return response

class QuotationUpdateView(LoginRequiredMixin, UpdateView):
    model = Quotation
    template_name = 'sales/quotation/form.html'
    fields = ['customer', 'status', 'quotation_date', 'valid_until', 'event_start_date', 'event_end_date', 'event_location', 'tax_rate', 'discount_percentage', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('name')
        
        # Get recent items for suggestions
        recent_items = QuotationItem.objects.values('description', 'unit_price').annotate(
            count=Count('id')
        ).order_by('-count')[:20]
        
        # Convert to JSON for JavaScript
        existing_items = []
        for item in recent_items:
            existing_items.append({
                'description': item['description'],
                'unit_price': float(item['unit_price'])
            })
        
        context['existing_items'] = json.dumps(existing_items)
        context['today'] = datetime.now().date().isoformat()
        
        # Load existing items for editing
        if self.object:
            context['quotation_items'] = list(self.object.items.values(
                'description', 'quantity', 'unit_price', 'line_total'
            ))
        
        return context
    
    def form_valid(self, form):
        # Save the quotation first
        response = super().form_valid(form)
        quotation = form.instance
        
        # Clear existing items
        quotation.items.all().delete()
        
        # Process items data
        item_index = 0
        while f'items-{item_index}-description' in self.request.POST:
            description = self.request.POST.get(f'items-{item_index}-description')
            quantity = self.request.POST.get(f'items-{item_index}-quantity')
            unit_price = self.request.POST.get(f'items-{item_index}-unit_price')
            
            if description and quantity and unit_price:
                QuotationItem.objects.create(
                    quotation=quotation,
                    description=description,
                    quantity=Decimal(quantity),
                    unit_price=Decimal(unit_price)
                )
            item_index += 1
        
        # Calculate totals
        quotation.calculate_totals()
        
        messages.success(self.request, 'Quotation updated successfully!')
        return response

class QuotationDeleteView(LoginRequiredMixin, DeleteView):
    model = Quotation
    template_name = 'sales/quotation/confirm_delete.html'
    success_url = reverse_lazy('quotation-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Quotation deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Invoice Views
class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'sales/invoice/list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Invoice.objects.select_related('customer', 'created_by')
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'sales/invoice/detail.html'
    context_object_name = 'invoice'

class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    template_name = 'sales/invoice/form.html'
    fields = ['customer', 'quotation', 'invoice_date', 'due_date', 'event_start_date', 'event_end_date', 'event_location', 'tax_rate', 'discount_percentage', 'notes']
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Auto-generate invoice number
        last_invoice = Invoice.objects.order_by('-id').first()
        if last_invoice:
            next_number = int(last_invoice.invoice_number.split('-')[-1]) + 1
        else:
            next_number = 1
        form.instance.invoice_number = f"INV-{next_number:05d}"
        messages.success(self.request, 'Invoice created successfully!')
        return super().form_valid(form)

class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    template_name = 'sales/invoice/form.html'
    fields = ['customer', 'status', 'invoice_date', 'due_date', 'event_start_date', 'event_end_date', 'event_location', 'tax_rate', 'discount_percentage', 'notes']
    
    def form_valid(self, form):
        messages.success(self.request, 'Invoice updated successfully!')
        return super().form_valid(form)

class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice
    template_name = 'sales/invoice/confirm_delete.html'
    success_url = reverse_lazy('invoice-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Invoice deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Receipt Views
class ReceiptListView(LoginRequiredMixin, ListView):
    model = Receipt
    template_name = 'sales/receipt/list.html'
    context_object_name = 'receipts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Receipt.objects.select_related('customer', 'invoice', 'created_by')
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(
                Q(receipt_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(invoice__invoice_number__icontains=search)
            )
            
        return queryset

class ReceiptDetailView(LoginRequiredMixin, DetailView):
    model = Receipt
    template_name = 'sales/receipt/detail.html'
    context_object_name = 'receipt'

class ReceiptCreateView(LoginRequiredMixin, CreateView):
    model = Receipt
    template_name = 'sales/receipt/form.html'
    fields = ['invoice', 'customer', 'amount', 'payment_method', 'payment_date', 'reference_number', 'notes']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add date picker widget
        form.fields['payment_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        # Set default value to today
        from datetime import date
        form.fields['payment_date'].initial = date.today()
        # Set amount default to 0.00
        form.fields['amount'].initial = Decimal('0.00')
        form.fields['amount'].widget.attrs.update({'step': '0.01', 'min': '0'})
        return form
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Auto-generate receipt number
        last_receipt = Receipt.objects.order_by('-id').first()
        if last_receipt:
            next_number = int(last_receipt.receipt_number.split('-')[-1]) + 1
        else:
            next_number = 1
        form.instance.receipt_number = f"REC-{next_number:05d}"

        response = super().form_valid(form)
        # Keep invoice paid balances in sync through finance allocation service.
        from finance.services import ensure_receipt_default_allocation, recalculate_customer_invoices
        ensure_receipt_default_allocation(self.object)
        recalculate_customer_invoices(self.object.customer)

        messages.success(self.request, 'Receipt created successfully!')
        return response

class ReceiptUpdateView(LoginRequiredMixin, UpdateView):
    model = Receipt
    template_name = 'sales/receipt/form.html'
    fields = ['amount', 'payment_method', 'payment_date', 'reference_number', 'notes']
    
    def form_valid(self, form):
        response = super().form_valid(form)
        from finance.models import PaymentAllocation
        from finance.services import recalculate_customer_invoices

        allocations = PaymentAllocation.objects.filter(receipt=self.object)
        if not allocations.exists():
            PaymentAllocation.objects.create(receipt=self.object, invoice=self.object.invoice, amount=self.object.amount)
        elif allocations.count() == 1 and allocations.first().invoice_id == self.object.invoice_id:
            allocation = allocations.first()
            allocation.amount = self.object.amount
            allocation.save(update_fields=['amount', 'updated_at'])
        else:
            allocated_total = allocations.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            if allocated_total != self.object.amount:
                messages.warning(
                    self.request,
                    'Receipt amount changed. Allocation total differs from receipt amount; please review allocations.',
                )

        recalculate_customer_invoices(self.object.customer)
        messages.success(self.request, 'Receipt updated successfully!')
        return response

class ReceiptDeleteView(LoginRequiredMixin, DeleteView):
    model = Receipt
    template_name = 'sales/receipt/confirm_delete.html'
    success_url = reverse_lazy('receipt-list')
    
    def delete(self, request, *args, **kwargs):
        receipt = self.get_object()
        customer = receipt.customer
        response = super().delete(request, *args, **kwargs)
        from finance.services import recalculate_customer_invoices
        recalculate_customer_invoices(customer)
        messages.success(request, 'Receipt deleted successfully!')
        return response

# AJAX Views for dynamic forms
@login_required
def get_customer_data(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
        data = {
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'company': customer.company,
        }
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)

@login_required
def convert_quotation_to_invoice(request, quotation_id):
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    if request.method == 'POST':
        # Create invoice from quotation
        last_invoice = Invoice.objects.order_by('-id').first()
        if last_invoice:
            next_number = int(last_invoice.invoice_number.split('-')[-1]) + 1
        else:
            next_number = 1
        
        invoice = Invoice.objects.create(
            invoice_number=f"INV-{next_number:05d}",
            customer=quotation.customer,
            quotation=quotation,
            created_by=request.user,
            invoice_date=date.today(),
            due_date=request.POST.get('due_date'),
            subtotal=quotation.subtotal,
            discount_percentage=quotation.discount_percentage,
            discount_amount=quotation.discount_amount,
            tax_rate=quotation.tax_rate,
            tax_amount=quotation.tax_amount,
            total_amount=quotation.total_amount,
            notes=quotation.notes,
            # Copy event fields from quotation
            event_start_date=quotation.event_start_date,
            event_end_date=quotation.event_end_date,
            event_location=quotation.event_location,
        )
        
        # Copy quotation items to invoice items
        for item in quotation.items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
        
        # Update quotation status
        quotation.status = 'accepted'
        quotation.save()
        
        messages.success(request, f'Invoice {invoice.invoice_number} created from quotation {quotation.quotation_number}!')
        return redirect('invoice-detail', pk=invoice.pk)
    
    return render(request, 'sales/quotation/convert_to_invoice.html', {'quotation': quotation})

@login_required
def analytics_view(request):
    """Analytics and reporting view"""
    from datetime import date, timedelta
    from django.db.models import Count, Avg
    
    today = date.today()
    
    # Financial metrics
    total_invoiced = Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = Invoice.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
    total_outstanding = total_invoiced - total_paid
    
    # Aging analysis
    current_due = Invoice.objects.filter(
        due_date__gte=today,
        status__in=['sent', 'overdue']
    ).aggregate(Sum('total_amount'), Count('id'))
    
    overdue_1_30 = Invoice.objects.filter(
        due_date__lt=today,
        due_date__gte=today - timedelta(days=30),
        status__in=['sent', 'overdue']
    ).aggregate(Sum('total_amount'), Count('id'))
    
    overdue_31_60 = Invoice.objects.filter(
        due_date__lt=today - timedelta(days=30),
        due_date__gte=today - timedelta(days=60),
        status__in=['sent', 'overdue']
    ).aggregate(Sum('total_amount'), Count('id'))
    
    overdue_60_plus = Invoice.objects.filter(
        due_date__lt=today - timedelta(days=60),
        status__in=['sent', 'overdue']
    ).aggregate(Sum('total_amount'), Count('id'))
    
    # Top customers analysis
    top_customers = get_top_outstanding_customers()[:10]
    
    # Payment method statistics
    payment_stats = Receipt.objects.values('payment_method').annotate(
        total_amount=Sum('amount'),
        count=Count('id'),
        avg_amount=Avg('amount')
    ).order_by('-total_amount')
    
    # Monthly trends (last 12 months)
    monthly_data = []
    for i in range(12):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_invoices = Invoice.objects.filter(
            invoice_date__range=[month_start, month_end]
        ).aggregate(
            total_amount=Sum('total_amount'),
            count=Count('id')
        )
        
        month_payments = Receipt.objects.filter(
            payment_date__range=[month_start, month_end]
        ).aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        
        monthly_data.append({
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%B %Y'),
            'invoices_amount': month_invoices['total_amount'] or 0,
            'invoices_count': month_invoices['count'] or 0,
            'payments_amount': month_payments['total_amount'] or 0,
            'payments_count': month_payments['count'] or 0,
        })
    
    monthly_data.reverse()  # Show oldest to newest
    
    context = {
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_outstanding': total_outstanding,
        'collection_rate': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0,
        
        # Aging buckets
        'current_due': current_due,
        'overdue_1_30': overdue_1_30,
        'overdue_31_60': overdue_31_60,
        'overdue_60_plus': overdue_60_plus,
        
        # Analysis data
        'top_customers': top_customers,
        'payment_stats': payment_stats,
        'monthly_data': monthly_data,
        
        # Counts
        'total_customers': Customer.objects.count(),
        'total_invoices': Invoice.objects.count(),
        'total_quotations': Quotation.objects.count(),
        'total_receipts': Receipt.objects.count(),
    }
    
    return render(request, 'sales/analytics.html', context)


# Enhanced HTML-based PDF Generation Views
from django.template.loader import render_to_string
import weasyprint
from decimal import Decimal

# Legacy PDF Generation Views for backward compatibility
from django.template.loader import get_template
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
import os

# Register Arabic font
ARABIC_FONT = 'Helvetica'  # Default fallback
try:
    # Prefer Cairo if provided in the project's fonts directory
    cairo_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Cairo-Regular.ttf')
    cairo_bold = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Cairo-Bold.ttf')
    if os.path.exists(cairo_path):
        pdfmetrics.registerFont(TTFont('Cairo', cairo_path))
        ARABIC_FONT = 'Cairo'
    # Try to register DejaVu Sans font which has good Unicode support
    if ARABIC_FONT == 'Helvetica':
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        ARABIC_FONT = 'DejaVuSans'
except:
    try:
        # Try Noto Sans Arabic font bundled with project
        font_path = os.path.join(os.path.dirname(__file__), '..', 'NotoSansArabic.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            ARABIC_FONT = 'ArabicFont'
    except:
        pass

def process_arabic_text(text):
    """Process Arabic text for proper display in PDF"""
    try:
        text_str = str(text) if text else ""
        if not text_str.strip():  # Return empty string if text is empty/None
            return ""
        if any('\u0600' <= char <= '\u06FF' for char in text_str):
            reshaped_text = arabic_reshaper.reshape(text_str)
            return get_display(reshaped_text)
        return text_str
    except:
        return str(text) if text else ""

def get_font_for_text(text):
    """Return appropriate font based on text content"""
    return ARABIC_FONT  # Use DejaVu Sans for all content

def generate_invoice_pdf(request, pk):
    """Generate PDF for invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Create BytesIO buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles with Arabic font support
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue,
        fontName=ARABIC_FONT
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue,
        fontName=ARABIC_FONT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName='Helvetica'
    )
    
    # Build document content
    content = []
    
    # Title
    content.append(Paragraph("INVOICE", title_style))
    content.append(Spacer(1, 20))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', invoice.invoice_number],
        ['Invoice Date:', invoice.invoice_date.strftime('%Y-%m-%d')],
        ['Due Date:', invoice.due_date.strftime('%Y-%m-%d')],
        ['Status:', invoice.get_status_display()],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    content.append(invoice_table)
    content.append(Spacer(1, 20))
    
    # Customer info
    content.append(Paragraph("Bill To:", header_style))
    # Use DejaVu Sans for customer info
    customer_style = ParagraphStyle('CustomerStyle', parent=normal_style, fontName=ARABIC_FONT)
    
    customer_info = f"""
    {process_arabic_text(invoice.customer.name)}<br/>
    {process_arabic_text(invoice.customer.company or '')}<br/>
    {process_arabic_text(invoice.customer.email)}<br/>
    {process_arabic_text(invoice.customer.phone or '')}<br/>
    {process_arabic_text(invoice.customer.address or '')}
    """
    content.append(Paragraph(customer_info, customer_style))
    content.append(Spacer(1, 20))
    
    # Items table
    content.append(Paragraph("Items:", header_style))
    
    items_data = [['Description', 'Quantity', 'Unit Price (QAR)', 'Total (QAR)']]
    
    for item in invoice.items.all():
        items_data.append([
            process_arabic_text(item.description),
            str(item.quantity),
            f'{item.unit_price:,.2f}',
            f'{item.line_total:,.2f}'
        ])
    
    # Set font based on content
    has_arabic = any(any('\u0600' <= char <= '\u06FF' for char in str(row[0])) for row in items_data[1:])
    table_font = ARABIC_FONT if has_arabic else 'Helvetica'
    
    # Add totals
    items_data.extend([
        ['', '', 'Subtotal:', f'{invoice.subtotal:,.2f} QAR'],
        ['', '', 'Tax:', f'{invoice.tax_amount:,.2f} QAR'],
        ['', '', 'Total Amount:', f'{invoice.total_amount:,.2f} QAR'],
        ['', '', 'Paid Amount:', f'{invoice.paid_amount:,.2f} QAR'],
        ['', '', 'Outstanding:', f'{invoice.balance_due:,.2f} QAR'],
    ])
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), table_font),
        ('GRID', (0, 0), (-1, len(items_data)-5), 0.5, colors.black),
        
        # Total rows
        ('FONTNAME', (0, -5), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    
    content.append(items_table)
    
    # Notes
    if invoice.notes:
        content.append(Spacer(1, 20))
        content.append(Paragraph("Notes:", header_style))
        # Use DejaVu Sans for notes
        notes_style = ParagraphStyle('NotesStyle', parent=normal_style, fontName=ARABIC_FONT)
        content.append(Paragraph(process_arabic_text(invoice.notes), notes_style))
    
    # Build PDF
    doc.build(content)
    
    # Get PDF data
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    response.write(pdf)
    
    return response


def generate_quotation_pdf(request, pk):
    """Generate PDF for quotation"""
    quotation = get_object_or_404(Quotation, pk=pk)
    
    # Create BytesIO buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles with Arabic font support
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkgreen,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkgreen,
        fontName=ARABIC_FONT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=ARABIC_FONT
    )
    
    # Build document content
    content = []
    
    # Title
    content.append(Paragraph("QUOTATION", title_style))
    content.append(Spacer(1, 20))
    
    # Quotation details
    quotation_data = [
        ['Quotation Number:', quotation.quotation_number],
        ['Quotation Date:', quotation.quotation_date.strftime('%Y-%m-%d')],
        ['Valid Until:', quotation.valid_until.strftime('%Y-%m-%d')],
        ['Status:', quotation.get_status_display()],
    ]
    
    quotation_table = Table(quotation_data, colWidths=[2*inch, 3*inch])
    quotation_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    content.append(quotation_table)
    content.append(Spacer(1, 20))
    
    # Customer info
    content.append(Paragraph("Quote For:", header_style))
    # Use DejaVu Sans for customer info
    customer_style = ParagraphStyle('CustomerStyle', parent=normal_style, fontName=ARABIC_FONT)
    
    customer_info = f"""
    {process_arabic_text(quotation.customer.name)}<br/>
    {process_arabic_text(quotation.customer.company or '')}<br/>
    {process_arabic_text(quotation.customer.email)}<br/>
    {process_arabic_text(quotation.customer.phone or '')}<br/>
    {process_arabic_text(quotation.customer.address or '')}
    """
    content.append(Paragraph(customer_info, customer_style))
    content.append(Spacer(1, 20))
    
    # Items table
    content.append(Paragraph("Items:", header_style))
    
    items_data = [['Description', 'Quantity', 'Unit Price (QAR)', 'Total (QAR)']]
    
    for item in quotation.items.all():
        items_data.append([
            process_arabic_text(item.description),
            str(item.quantity),
            f'{item.unit_price:,.2f}',
            f'{item.line_total:,.2f}'
        ])
    
    # Set font based on content
    has_arabic = any(any('\u0600' <= char <= '\u06FF' for char in str(row[0])) for row in items_data[1:])
    table_font = ARABIC_FONT if has_arabic else 'Helvetica'
    
    # Add totals
    items_data.extend([
        ['', '', 'Subtotal:', f'{quotation.subtotal:,.2f} QAR'],
        ['', '', 'Tax:', f'{quotation.tax_amount:,.2f} QAR'],
        ['', '', 'Total Amount:', f'{quotation.total_amount:,.2f} QAR'],
    ])
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), table_font),
        ('GRID', (0, 0), (-1, len(items_data)-3), 0.5, colors.black),
        
        # Total rows
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    
    content.append(items_table)
    
    # Notes
    if quotation.notes:
        content.append(Spacer(1, 20))
        content.append(Paragraph("Notes:", header_style))
        # Use DejaVu Sans for notes
        notes_style = ParagraphStyle('NotesStyle', parent=normal_style, fontName=ARABIC_FONT)
        content.append(Paragraph(process_arabic_text(quotation.notes), notes_style))
    
    # Build PDF
    doc.build(content)
    
    # Get PDF data
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quotation_{quotation.quotation_number}.pdf"'
    response.write(pdf)
    
    return response


def generate_receipt_pdf(request, pk):
    """Generate PDF for receipt"""
    receipt = get_object_or_404(Receipt, pk=pk)
    
    # Create BytesIO buffer
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Styles with Arabic font support
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.purple,
        fontName=ARABIC_FONT
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.purple,
        fontName=ARABIC_FONT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=ARABIC_FONT
    )
    
    # Build document content
    content = []
    
    # Title
    content.append(Paragraph("PAYMENT RECEIPT", title_style))
    content.append(Spacer(1, 20))
    
    # Receipt details
    receipt_data = [
        ['Receipt Number:', receipt.receipt_number],
        ['Payment Date:', receipt.payment_date.strftime('%Y-%m-%d')],
        ['Payment Method:', receipt.get_payment_method_display()],
        ['Reference Number:', receipt.reference_number or 'N/A'],
        ['Amount Paid:', f'{receipt.amount:,.2f} QAR'],
    ]
    
    receipt_table = Table(receipt_data, colWidths=[2*inch, 3*inch])
    receipt_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (-1, -1), (-1, -1), colors.lightgreen),
        ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    content.append(receipt_table)
    content.append(Spacer(1, 20))
    
    # Invoice details
    content.append(Paragraph("Payment For:", header_style))
    invoice_info = f"""
    Invoice Number: {receipt.invoice.invoice_number}<br/>
    Customer: {receipt.invoice.customer.name}<br/>
    Invoice Total: {receipt.invoice.total_amount:,.2f} QAR<br/>
    Previous Payments: {receipt.invoice.paid_amount - receipt.amount:,.2f} QAR<br/>
    This Payment: {receipt.amount:,.2f} QAR<br/>
    Remaining Balance: {receipt.invoice.balance_due:,.2f} QAR
    """
    content.append(Paragraph(invoice_info, normal_style))
    content.append(Spacer(1, 20))
    
    # Notes
    if receipt.notes:
        content.append(Paragraph("Notes:", header_style))
        # Use DejaVu Sans for notes
        notes_style = ParagraphStyle('NotesStyle', parent=normal_style, fontName=ARABIC_FONT)
        content.append(Paragraph(process_arabic_text(receipt.notes), notes_style))
    
    # Build PDF
    doc.build(content)
    
    # Get PDF data
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.receipt_number}.pdf"'
    response.write(pdf)
    
    return response


# Enhanced Invoice Creation View with Advanced Features
@login_required
def invoice_create_enhanced(request):
    """Enhanced invoice creation with customer/item fetching"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.POST.get('customer')
            invoice_date = request.POST.get('invoice_date')
            due_date = request.POST.get('due_date')
            notes = request.POST.get('notes', '')
            payment_method = request.POST.get('payment_method', 'cash')
            
            # Event details
            event_start_date = request.POST.get('event_start_date')
            event_end_date = request.POST.get('event_end_date')
            event_location = request.POST.get('event_location', '')
            
            # Discount handling - check which field has a value
            discount_percentage = Decimal(request.POST.get('discount_percentage', '0'))
            discount_amount_input = Decimal(request.POST.get('discount_amount_input', '0'))
            tax_rate = Decimal(request.POST.get('tax_rate', '0'))
            
            # Validate customer
            customer = get_object_or_404(Customer, id=customer_id)
            
            # Auto-generate invoice number
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                next_number = int(last_invoice.invoice_number.split('-')[-1]) + 1
            else:
                next_number = 1
            invoice_number = f"INV-{next_number:05d}"
            
            # Create invoice
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                created_by=request.user,
                invoice_date=invoice_date,
                due_date=due_date,
                event_start_date=event_start_date if event_start_date else None,
                event_end_date=event_end_date if event_end_date else None,
                event_location=event_location,
                tax_rate=tax_rate,
                notes=notes,
                payment_method=payment_method
            )
            
            # Add invoice items
            item_index = 0
            subtotal = Decimal('0')
            
            while f'items-{item_index}-description' in request.POST:
                description = request.POST.get(f'items-{item_index}-description')
                quantity = request.POST.get(f'items-{item_index}-quantity')
                unit_price = request.POST.get(f'items-{item_index}-unit_price')
                
                if description and quantity and unit_price:
                    quantity = Decimal(quantity)
                    unit_price = Decimal(unit_price)
                    line_total = quantity * unit_price
                    
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total
                    )
                    subtotal += line_total
                item_index += 1
            
            # Calculate discount
            discount_amount = Decimal('0')
            if discount_amount_input > 0:
                # Fixed amount discount was entered
                discount_amount = discount_amount_input
                # Calculate percentage for display
                if subtotal > 0:
                    discount_percentage = (discount_amount / subtotal) * 100
            elif discount_percentage > 0:
                # Percentage discount was entered
                discount_amount = subtotal * (discount_percentage / 100)
            
            # Update invoice totals
            invoice.discount_percentage = discount_percentage
            invoice.discount_amount = discount_amount
            invoice.subtotal = subtotal
            invoice.tax_amount = (subtotal - discount_amount) * (tax_rate / 100)
            invoice.total_amount = subtotal - discount_amount + invoice.tax_amount
            invoice.save()
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice_id': invoice.id,
                    'redirect_url': invoice.get_absolute_url()
                })
            else:
                # Regular form submission - redirect directly
                return redirect('invoice-detail', pk=invoice.pk)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - show form
    customers = Customer.objects.all().order_by('name')
    
    # Get recent items for suggestions
    recent_items = InvoiceItem.objects.values('description', 'unit_price').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    # Convert to JSON for JavaScript
    existing_items = []
    for item in recent_items:
        existing_items.append({
            'description': item['description'],
            'unit_price': float(item['unit_price'])
        })
    
    context = {
        'customers': customers,
        'payment_methods': Invoice.PAYMENT_METHOD_CHOICES,
        'today': datetime.now().date().isoformat(),
        'existing_items': json.dumps(existing_items)
    }
    return render(request, 'sales/invoice_create_enhanced.html', context)


# Enhanced HTML-based PDF Generation
@login_required
def generate_invoice_html_pdf(request, pk):
    """Generate HTML-based PDF for invoice with advanced styling"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Render HTML template
    html_string = render_to_string('sales/invoice_pdf.html', {
        'invoice': invoice,
        'company_info': {
            'name': 'InvoiceSystem Pro',
            'address': 'Doha, Qatar',
            'phone': '+974 xxxx xxxx',
            'email': 'info@invoicesystem.com',
            'website': 'www.invoicesystem.com'
        }
    })
    
    # CSS for PDF styling - inline to avoid external dependencies
    font_dir = '/root/invsys/fonts'
    css_string = """
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        body { 
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', Arial, sans-serif;
            margin: 0; 
            padding: 20px; 
            color: #1a202c;
            line-height: 1.6;
            font-size: 14px;
        }
        
    css_string = css_string.replace('<<FONT_DIR>>', font_dir)
        .invoice-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
        }
        
        .company-info h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
        }
        
        .invoice-details {
            background: #f7fafc;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        
        .customer-info {
            background: white;
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 2rem;
        }
        
        .items-table th {
            background: #4a5568;
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }
        
        .items-table td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .items-table tr:nth-child(even) {
            background: #f7fafc;
        }
        
        .totals-section {
            background: #4a5568;
            color: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-top: 2rem;
        }
        
        .arabic-text {
            direction: rtl;
            text-align: right;
        }
        
        .amount {
            font-weight: 600;
            font-size: 1.1em;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status-paid { background: #48bb78; color: white; }
        .status-sent { background: #4299e1; color: white; }
        .status-overdue { background: #f56565; color: white; }
        .status-draft { background: #a0aec0; color: white; }
        
        .row { display: flex; flex-wrap: wrap; }
        .col { flex: 1; padding: 0 15px; }
        .text-right { text-align: right; }
        .mb-3 { margin-bottom: 1rem; }
        .mt-4 { margin-top: 1.5rem; }
    """
    
    # Generate PDF using WeasyPrint
    html_doc = weasyprint.HTML(string=html_string)
    css_doc = weasyprint.CSS(string=css_string)
    pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc])
    
    # Return PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    response.write(pdf_bytes)
    
    return response


# AJAX endpoints for enhanced invoice creation
@login_required
def get_customer_details(request, customer_id):
    """Get detailed customer information for invoice creation"""
    try:
        customer = Customer.objects.get(id=customer_id)
        
        # Get recent invoices for this customer
        recent_invoices = customer.invoices.order_by('-invoice_date')[:5]
        
        # Calculate customer statistics
        total_invoiced = customer.invoices.aggregate(
            total=Sum('total_amount'))['total'] or 0
        total_paid = customer.invoices.aggregate(
            total=Sum('paid_amount'))['total'] or 0
        outstanding_balance = total_invoiced - total_paid
        
        data = {
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'company': customer.company,
            'total_invoiced': float(total_invoiced),
            'total_paid': float(total_paid),
            'outstanding_balance': float(outstanding_balance),
            'recent_invoices': [
                {
                    'number': inv.invoice_number,
                    'date': inv.invoice_date.strftime('%Y-%m-%d'),
                    'amount': float(inv.total_amount),
                    'status': inv.status
                } for inv in recent_invoices
            ]
        }
        return JsonResponse(data)
        
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)


@login_required
def search_customers(request):
    """Search customers for autocomplete"""
    query = request.GET.get('q', '')
    customers = Customer.objects.filter(
        Q(name__icontains=query) |
        Q(company__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    ).order_by('name')[:10]
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'company': customer.company or '',
            'email': customer.email or '',
            'phone': customer.phone,
            'display_name': f"{customer.name} - {customer.phone}"
        })
    
    return JsonResponse({'customers': results})


@login_required
def get_recent_invoice_items(request):
    """Get recent invoice items for suggestions"""
    items = InvoiceItem.objects.values(
        'description', 'unit_price'
    ).annotate(
        usage_count=Count('id'),
        avg_price=Avg('unit_price')
    ).order_by('-usage_count')[:20]
    
    suggestions = []
    for item in items:
        suggestions.append({
            'description': item['description'],
            'unit_price': float(item['avg_price']),
            'usage_count': item['usage_count']
        })
    
    return JsonResponse({'items': suggestions})


# WeasyPrint HTML-to-PDF Generation
try:
    import weasyprint
    from weasyprint import HTML, CSS
    from django.template.loader import render_to_string
    import tempfile
    import os
    
    @login_required
    def generate_invoice_pdf_html(request, invoice_id):
        """Generate PDF from HTML template using WeasyPrint for better Arabic support"""
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Get logo path
        logo_path = '/root/invsys/media/logo.png'
        logo_url = f'file://{logo_path}'
        
        # Render HTML template
        html_content = render_to_string('sales/invoice_pdf.html', {
            'invoice': invoice,
            'logo_path': logo_url,
        })
        
        # Create CSS for Arabic fonts with @font-face declarations
        font_dir = '/root/invsys/fonts'
        css_content = """
        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }

        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }

        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: ltr;
        }

        .arabic-text {
            font-family: 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: rtl;
            unicode-bidi: bidi-override;
            text-align: right;
        }

        /* Apply Arabic font to potentially Arabic content */
        td, p, div {
            font-family: 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
        }
        """
        css_content = css_content.replace('<<FONT_DIR>>', font_dir)
        
        try:
            # Generate PDF using WeasyPrint
            html_doc = HTML(string=html_content, base_url=request.build_absolute_uri())
            css_doc = CSS(string=css_content)
            
            pdf = html_doc.write_pdf(stylesheets=[css_doc])
            
            # Create response
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_number}.pdf"'
            
            return response
            
        except Exception as e:
            messages.error(request, f'PDF generation failed: {str(e)}')
            return redirect('invoice-detail', pk=invoice.id)
    
    @login_required
    def generate_quotation_pdf_html(request, quotation_id):
        """Generate PDF from HTML template using WeasyPrint for better Arabic support"""
        quotation = get_object_or_404(Quotation, id=quotation_id)
        
        # Get logo path
        logo_path = '/root/invsys/media/logo.png'
        logo_url = f'file://{logo_path}'
        
        # Render HTML template
        html_content = render_to_string('sales/quotation_pdf.html', {
            'quotation': quotation,
            'logo_path': logo_url,
        })
        
        # Create CSS for Arabic fonts with @font-face declarations (prefer Cairo if present)
        font_dir = '/root/invsys/fonts'
        css_content = """
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        /* Fallback to Noto if Cairo not available */
        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }

        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: ltr;
        }

        .arabic-text {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: rtl;
            unicode-bidi: bidi-override;
            text-align: right;
        }

        .company-name-arabic {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
        }

        /* Apply Arabic font to potentially Arabic content */
        td, p, div {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
        }
        """
        css_content = css_content.replace('<<FONT_DIR>>', font_dir)
        
        try:
            # Generate PDF using WeasyPrint
            html_doc = HTML(string=html_content, base_url=request.build_absolute_uri())
            css_doc = CSS(string=css_content)
            
            pdf = html_doc.write_pdf(stylesheets=[css_doc])
            
            # Create response
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="quotation_{quotation.quotation_number}.pdf"'
            
            return response
            
        except Exception as e:
            messages.error(request, f'PDF generation failed: {str(e)}')
            return redirect('quotation-detail', pk=quotation.id)

    @login_required
    def generate_receipt_pdf_html(request, receipt_id):
        """Generate PDF from HTML template for receipts using WeasyPrint"""
        receipt = get_object_or_404(Receipt, id=receipt_id)

        # Get logo path
        logo_path = '/root/invsys/media/logo.png'
        logo_url = f'file://{logo_path}'

        # Render HTML template
        html_content = render_to_string('sales/receipt/receipt_pdf.html', {
            'receipt': receipt,
            'logo_path': logo_url,
        })

        # Use same font directory as other PDFs
        font_dir = '/root/invsys/fonts'
        css_content = """
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'CairoLocal';
            src: url('file://<<FONT_DIR>>/Cairo-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }
        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
        }
        @font-face {
            font-family: 'Noto Sans Arabic';
            src: url('file://<<FONT_DIR>>/NotoSansArabic-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
        }

        @page { size: A4; margin: 2cm; }

        body {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: ltr;
        }

        .arabic-text {
            font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif;
            direction: rtl;
            unicode-bidi: bidi-override;
            text-align: right;
        }

        td, p, div { font-family: 'CairoLocal', 'Cairo', 'Noto Sans Arabic', 'DejaVu Sans', Arial, sans-serif; }
        """
        css_content = css_content.replace('<<FONT_DIR>>', font_dir)

        try:
            html_doc = HTML(string=html_content, base_url=request.build_absolute_uri())
            css_doc = CSS(string=css_content)
            pdf = html_doc.write_pdf(stylesheets=[css_doc])

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="receipt_{receipt.receipt_number}.pdf"'
            return response
        except Exception as e:
            messages.error(request, f'PDF generation failed: {str(e)}')
            return redirect('receipt-detail', pk=receipt.id)

except ImportError:
    # WeasyPrint not available, create a placeholder function
    @login_required
    def generate_invoice_pdf_html(request, invoice_id):
        messages.error(request, 'WeasyPrint is not installed. Please install it for HTML-based PDF generation.')
        return redirect('invoice-detail', pk=invoice_id)
    
    @login_required
    def generate_quotation_pdf_html(request, quotation_id):
        messages.error(request, 'WeasyPrint is not installed. Please install it for HTML-based PDF generation.')
        return redirect('quotation-detail', pk=quotation_id)

