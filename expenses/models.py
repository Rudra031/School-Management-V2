import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class ExpenseCategory(BaseModel):
    """
    Operating Expense Categories (e.g. Utilities, Maintenance, Consumables, Software, Events, Office Supplies).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Expense Category')
        verbose_name_plural = _('Expense Categories')

    def __str__(self):
        return self.name


class Expense(BaseModel):
    """
    Operational Expenditure and Payment Voucher.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CHEQUE = 'CHEQUE', _('Cheque')
        CARD = 'CARD', _('Debit / Corporate Card')

    voucher_number = models.CharField(max_length=50, unique=True, db_index=True)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    vendor_name = models.CharField(max_length=150, blank=True, help_text=_('Supplier or Vendor Name'))
    receipt_file = models.FileField(upload_to='expenses/receipts/%Y/%m/', blank=True, null=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name = _('Expense Voucher')
        verbose_name_plural = _('Expense Vouchers')

    def __str__(self):
        return f"{self.voucher_number} - {self.title} (${self.amount})"
