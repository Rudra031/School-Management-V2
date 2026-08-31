from django.urls import path
from inventory import views

app_name = 'inventory'

urlpatterns = [
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    path('items/', views.InventoryItemListView.as_view(), name='item_list'),
    path('items/create/', views.InventoryItemCreateView.as_view(), name='item_create'),
    path('allocations/', views.AssetAllocationListView.as_view(), name='allocation_list'),
    path('allocations/create/', views.AssetAllocationCreateView.as_view(), name='allocation_create'),
    path('allocations/<uuid:pk>/return/', views.AssetAllocationReturnView.as_view(), name='allocation_return'),
]
