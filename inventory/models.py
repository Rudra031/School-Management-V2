import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class AssetCategory(BaseModel):
    """
    Asset and Inventory Category (e.g. IT Equipment, Lab Equipment, Furniture, Sports Gear).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Asset Category')
        verbose_name_plural = _('Asset Categories')

    def __str__(self):
        return self.name


class InventoryItem(BaseModel):
    """
    Fixed Asset and Consumable Inventory Item Master.
    """
    item_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    quantity_total = models.PositiveIntegerField(default=1)
    quantity_in_use = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=30, default='Pieces', help_text=_('e.g. Pieces, Sets, Boxes, Units'))
    
    reorder_threshold = models.PositiveIntegerField(default=5, help_text=_('Trigger low stock warning'))
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    location = models.CharField(max_length=100, blank=True, help_text=_('e.g. Lab 2, Storage Room B'))

    class Meta:
        ordering = ['name']
        verbose_name = _('Inventory Item')
        verbose_name_plural = _('Inventory Items')

    def __str__(self):
        return f"{self.name} ({self.item_code}) - {self.available_quantity}/{self.quantity_total} {self.unit}"

    @property
    def available_quantity(self):
        return max(0, self.quantity_total - self.quantity_in_use)

    @property
    def is_low_stock(self):
        return self.available_quantity <= self.reorder_threshold

    @property
    def total_asset_value(self):
        return self.quantity_total * self.cost_per_unit


class AssetAllocation(BaseModel):
    """
    Asset Allocation & Custody record to staff or departmental labs.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('In Active Custody')
        RETURNED = 'RETURNED', _('Returned to Inventory')
        DAMAGED = 'DAMAGED', _('Reported Damaged / Written Off')

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='allocations')
    allocated_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_assets'
    )
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_assets'
    )
    quantity = models.PositiveIntegerField(default=1)
    allocated_date = models.DateField(default=timezone.now)
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-allocated_date', '-created_at']
        verbose_name = _('Asset Allocation')
        verbose_name_plural = _('Asset Allocations')

    def __str__(self):
        custodian = self.allocated_to_user.email if self.allocated_to_user else (self.department.name if self.department else "Unassigned")
        return f"{self.item.name} (Qty: {self.quantity}) -> {custodian}"
