from django.urls import path
from reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.ConsolidatedReportsHubView.as_view(), name='hub'),
    path('demographics/', views.StudentDemographicsReportView.as_view(), name='demographics'),
    path('financial/', views.FinancialIncomeExpenseReportView.as_view(), name='financial'),
    path('financial/export/', views.FinancialReportExportView.as_view(), name='financial_export'),
]
