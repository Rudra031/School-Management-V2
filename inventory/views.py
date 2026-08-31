from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView
from django.db import transaction, models
from django.db.models import Q, F, Sum
from django.contrib import messages
from django.utils import timezone

from inventory.models import AssetCategory, InventoryItem, AssetAllocation
from inventory.forms import AssetCategoryForm, InventoryItemForm, AssetAllocationForm
from core.permissions import SchoolAdminRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class InventoryDashboardView(SchoolAdminRequiredMixin, TemplateView):
    """
    Asset and Inventory Management Executive Dashboard.
    """
    template_name = 'inventory/inventory_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = InventoryItem.objects.filter(is_deleted=False).select_related('category')
        
        total_items_count = items.count()
        total_units = items.aggregate(Sum('quantity_total'))['quantity_total__sum'] or 0
        total_in_use = items.aggregate(Sum('quantity_in_use'))['quantity_in_use__sum'] or 0
        
        # Calculate total asset monetary valuation
        total_asset_val = sum((i.total_asset_value for i in items))
        
        # Low stock items list
        low_stock_items = [i for i in items if i.is_low_stock]
        active_allocations = AssetAllocation.objects.filter(status=AssetAllocation.Status.ACTIVE, is_deleted=False).select_related('item', 'allocated_to_user')

        context['total_items_count'] = total_items_count
        context['total_units'] = total_units
        context['total_in_use'] = total_in_use
        context['total_asset_val'] = total_asset_val
        context['low_stock_items'] = low_stock_items
        context['active_allocations'] = active_allocations[:10]
        return context


class InventoryItemListView(SchoolAdminRequiredMixin, ListView):
    model = InventoryItem
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 25

    def get_queryset(self):
        qs = InventoryItem.objects.filter(is_deleted=False).select_related('category')
        search = self.request.GET.get('search', '').strip()
        category_id = self.request.GET.get('category')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(item_code__icontains=search) | Q(location__icontains=search))
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = AssetCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class InventoryItemCreateView(SchoolAdminRequiredMixin, CreateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('inventory:item_list')

    def form_valid(self, form):
        messages.success(self.request, f"Inventory item '{form.cleaned_data['name']}' registered.")
        return super().form_valid(form)


class AssetAllocationListView(SchoolAdminRequiredMixin, ListView):
    model = AssetAllocation
    template_name = 'inventory/allocation_list.html'
    context_object_name = 'allocations'
    paginate_by = 25

    def get_queryset(self):
        return AssetAllocation.objects.filter(is_deleted=False).select_related('item', 'allocated_to_user', 'department')


class AssetAllocationCreateView(SchoolAdminRequiredMixin, CreateView):
    model = AssetAllocation
    form_class = AssetAllocationForm
    template_name = 'inventory/allocation_form.html'
    success_url = reverse_lazy('inventory:allocation_list')

    @transaction.atomic
    def form_valid(self, form):
        allocation = form.save(commit=False)
        item = allocation.item

        if allocation.quantity > item.available_quantity:
            messages.error(self.request, "Cannot allocate: Insufficient available quantity.")
            return self.form_invalid(form)

        item.quantity_in_use += allocation.quantity
        item.save()

        allocation.status = AssetAllocation.Status.ACTIVE
        allocation.save()

        messages.success(self.request, f"Allocated {allocation.quantity} unit(s) of '{item.name}'.")
        return redirect('inventory:allocation_list')


class AssetAllocationReturnView(SchoolAdminRequiredMixin, View):
    """
    Return allocated equipment back to available stock.
    """
    @transaction.atomic
    def post(self, request, pk):
        allocation = get_object_or_404(AssetAllocation, pk=pk)
        if allocation.status == AssetAllocation.Status.ACTIVE:
            allocation.status = AssetAllocation.Status.RETURNED
            allocation.return_date = timezone.now().date()
            allocation.save()

            allocation.item.quantity_in_use = max(0, allocation.item.quantity_in_use - allocation.quantity)
            allocation.item.save()

            messages.success(request, f"Returned {allocation.quantity} unit(s) of '{allocation.item.name}' to storage.")
        return redirect('inventory:allocation_list')
