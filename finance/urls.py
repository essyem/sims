from django.urls import path

from . import views


app_name = 'finance'


urlpatterns = [
    path('', views.FinanceDashboardView.as_view(), name='dashboard'),
    path('statements/customer/', views.CustomerStatementView.as_view(), name='customer-statement'),
    path('statements/customer/<int:customer_id>/', views.CustomerStatementView.as_view(), name='customer-statement-customer'),
    path('statements/customer/<int:customer_id>/pdf/', views.CustomerStatementPdfView.as_view(), name='customer-statement-pdf'),
    path('statement-runs/', views.StatementRunListView.as_view(), name='statement-run-list'),
    path('statement-runs/generate/', views.GenerateStatementRunsView.as_view(), name='statement-run-generate'),
    path('statement-runs/<int:pk>/mark-emailed/', views.MarkStatementEmailedView.as_view(), name='statement-run-mark-emailed'),
    path('profit-loss/', views.ProfitLossView.as_view(), name='profit-loss'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/create/', views.ExpenseCreateView.as_view(), name='expense-create'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense-update'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense-delete'),
    path('allocations/receipts/<int:receipt_id>/', views.ReceiptAllocationUpdateView.as_view(), name='receipt-allocation-update'),
]
