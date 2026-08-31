from django import forms
from django.utils.translation import gettext_lazy as _
from inventory.models import AssetCategory, InventoryItem, AssetAllocation

class AssetCategoryForm(forms.ModelForm):
    class Meta:
        model = AssetCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['item_code', 'name', 'category', 'quantity_total', 'quantity_in_use', 'unit', 'reorder_threshold', 'cost_per_unit', 'location']
        widgets = {
            'item_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. IT-LAP-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity_in_use': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'reorder_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AssetAllocationForm(forms.ModelForm):
    class Meta:
        model = AssetAllocation
        fields = ['item', 'allocated_to_user', 'department', 'quantity', 'allocated_date', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'allocated_to_user': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'allocated_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        qty = cleaned_data.get('quantity') or 1
        if item and qty > item.available_quantity:
            self.add_error('quantity', f"Only {item.available_quantity} units of '{item.name}' are available for allocation.")
        return cleaned_data
