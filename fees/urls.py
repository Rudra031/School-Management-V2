from django.urls import path
from fees import views

app_name = 'fees'

urlpatterns = [
    path('', views.FeeOverviewDashboardView.as_view(), name='overview'),
    path('pos/', views.FeePOSCounterView.as_view(), name='pos_counter'),
    path('receipts/<uuid:pk>/', views.FeeReceiptPrintView.as_view(), name='receipt_print'),
    path('receipts/<uuid:pk>/pdf/', views.FeeReceiptPDFDownloadView.as_view(), name='receipt_pdf'),
    path('defaulters/', views.FeeDefaultersListView.as_view(), name='defaulters_list'),
    path('concessions/', views.FeeConcessionListView.as_view(), name='concession_list'),
    path('concessions/create/', views.FeeConcessionCreateView.as_view(), name='concession_create'),
    path('concessions/assign/', views.StudentConcessionAssignView.as_view(), name='concession_assign'),
    path('structures/', views.FeeStructureListView.as_view(), name='structure_list'),
    path('structures/create/', views.FeeStructureCreateView.as_view(), name='structure_create'),
    path('structures/<uuid:pk>/edit/', views.FeeStructureUpdateView.as_view(), name='structure_edit'),
    path('structures/<uuid:pk>/delete/', views.FeeStructureDeleteView.as_view(), name='structure_delete'),
    path('fine-rules/create/', views.FeeFineRuleCreateView.as_view(), name='fine_rule_create'),
    path('invoices/', views.StudentFeeInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/batch-generate/', views.InvoiceBatchGenerationView.as_view(), name='invoice_batch_generate'),
    path('invoices/<uuid:pk>/', views.StudentFeeInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:pk>/pay/', views.FeePaymentCreateView.as_view(), name='invoice_pay'),
    path('invoices/<uuid:pk>/online-pay/', views.ParentOnlineFeePaymentView.as_view(), name='online_pay'),
]
