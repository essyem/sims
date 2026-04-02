from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer-update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer-delete'),
    
    # Quotation URLs
    path('quotations/', views.QuotationListView.as_view(), name='quotation-list'),
    path('quotations/create/', views.QuotationCreateView.as_view(), name='quotation-create'),
    path('quotations/<int:pk>/', views.QuotationDetailView.as_view(), name='quotation-detail'),
    path('quotations/<int:pk>/edit/', views.QuotationUpdateView.as_view(), name='quotation-update'),
    path('quotations/<int:pk>/delete/', views.QuotationDeleteView.as_view(), name='quotation-delete'),
    path('quotations/<int:quotation_id>/convert-to-invoice/', views.convert_quotation_to_invoice, name='convert-quotation-to-invoice'),
    
    # Invoice URLs
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice-update'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice-delete'),
    
    # Receipt URLs
    path('receipts/', views.ReceiptListView.as_view(), name='receipt-list'),
    path('receipts/create/', views.ReceiptCreateView.as_view(), name='receipt-create'),
    path('receipts/<int:pk>/', views.ReceiptDetailView.as_view(), name='receipt-detail'),
    path('receipts/<int:pk>/edit/', views.ReceiptUpdateView.as_view(), name='receipt-update'),
    path('receipts/<int:pk>/delete/', views.ReceiptDeleteView.as_view(), name='receipt-delete'),
    
    # AJAX URLs
    path('ajax/customer/<int:customer_id>/', views.get_customer_data, name='get-customer-data'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    
    # Enhanced Invoice Creation
    path('invoices/create-enhanced/', views.invoice_create_enhanced, name='invoice-create-enhanced'),
    
    # PDF Generation URLs
    path('invoices/<int:pk>/pdf/', views.generate_invoice_pdf, name='invoice-pdf'),
    path('invoices/<int:invoice_id>/html-pdf/', views.generate_invoice_pdf_html, name='invoice-html-pdf'),
    path('quotations/<int:pk>/pdf/', views.generate_quotation_pdf, name='quotation-pdf'),
    path('quotations/<int:quotation_id>/html-pdf/', views.generate_quotation_pdf_html, name='quotation-html-pdf'),
    path('receipts/<int:pk>/pdf/', views.generate_receipt_pdf, name='receipt-pdf'),
    path('receipts/<int:receipt_id>/html-pdf/', views.generate_receipt_pdf_html, name='receipt-html-pdf'),
    
    # Enhanced AJAX endpoints
    path('ajax/customer/<int:customer_id>/details/', views.get_customer_details, name='get-customer-details'),
    path('ajax/customers/search/', views.search_customers, name='search-customers'),
    path('ajax/items/recent/', views.get_recent_invoice_items, name='get-recent-items'),
]