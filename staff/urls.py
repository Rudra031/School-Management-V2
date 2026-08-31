from django.urls import path
from staff import views

app_name = 'staff'

urlpatterns = [
    path('', views.StaffListView.as_view(), name='staff_list'),
    path('create/', views.StaffCreateView.as_view(), name='staff_create'),
    path('export/', views.StaffExportView.as_view(), name='staff_export'),
    path('<uuid:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    path('<uuid:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),
    path('<uuid:pk>/salary-structure/', views.StaffSalaryStructureUpdateView.as_view(), name='staff_salary_structure'),

    # Payroll Engine
    path('payroll/dashboard/', views.PayrollDashboardView.as_view(), name='payroll_dashboard'),
    path('payroll/generate/', views.PayrollBatchGenerateView.as_view(), name='payroll_generate'),
    path('payroll/<uuid:pk>/', views.PayrollPeriodDetailView.as_view(), name='payroll_period_detail'),
    path('payroll/<uuid:pk>/approve/', views.PayrollPeriodApproveView.as_view(), name='payroll_period_approve'),
    path('payroll/<uuid:pk>/disburse/', views.PayrollPeriodDisburseView.as_view(), name='payroll_period_disburse'),
    
    # Salary Slips
    path('slips/<uuid:pk>/', views.SalarySlipDetailView.as_view(), name='salary_slip_detail'),
    path('slips/<uuid:pk>/print/', views.SalarySlipPrintView.as_view(), name='salary_slip_print'),
]
