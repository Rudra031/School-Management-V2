from django.urls import path
from expenses import views

app_name = 'expenses'

urlpatterns = [
    path('', views.ExpenseOverviewView.as_view(), name='overview'),
    path('list/', views.ExpenseListView.as_view(), name='list'),
    path('create/', views.ExpenseCreateView.as_view(), name='create'),
    path('export/', views.ExpenseExportView.as_view(), name='export'),
]
