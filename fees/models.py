import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class FeeCategory(BaseModel):
    """
    Categorization of fees (e.g., Tuition, Lab, Library, Admission, Sports, Exam, Annual).
    """
    class CategoryType(models.TextChoices):
        TUITION = 'TUITION', _('Tuition Fee')
        LAB = 'LAB', _('Science & Computer Lab Fee')
        EXAM = 'EXAM', _('Examination Fee')
        ACTIVITY = 'ACTIVITY', _('Sports & Co-Curricular Fee')
        DEVELOPMENT = 'DEVELOPMENT', _('Annual & School Development Charges')
        LIBRARY = 'LIBRARY', _('Library & Digital Resource Fee')
        ADMISSION = 'ADMISSION', _('One-Time Admission / Registration Fee')
        OTHER = 'OTHER', _('Other Institutional Charges')

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(
        max_length=30,
        choices=CategoryType.choices,
        default=CategoryType.TUITION,
        help_text=_('Standard accounting head')
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Fee Category')
        verbose_name_plural = _('Fee Categories')

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class FeeConcession(BaseModel):
    """
    Institutional Fee Concession & Scholarship Scheme (e.g. Sibling Discount 20%, Staff Ward 50%, EWS 100%).
    """
    class ConcessionType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', _('Percentage Discount (%)')
        FIXED_AMOUNT = 'FIXED_AMOUNT', _('Fixed Amount Discount (₹)')

    name = models.CharField(max_length=100, unique=True, help_text=_('e.g. Sibling Discount (20%), Staff Child (50%)'))
    code = models.CharField(max_length=30, unique=True, help_text=_('e.g. SIBLING_20, STAFF_50, EWS_100, MERIT_25'))
    concession_type = models.CharField(max_length=20, choices=ConcessionType.choices, default=ConcessionType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Percentage or Fixed Rupee amount'))
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Fee Concession')
        verbose_name_plural = _('Fee Concessions')

    def __str__(self):
        symbol = "%" if self.concession_type == self.ConcessionType.PERCENTAGE else "₹"
        return f"{self.name} - {self.discount_value}{symbol}"


class StudentConcession(BaseModel):
    """
    Mapping of a Concession rule to a student for an Academic Year.
    """
    student_enrollment = models.ForeignKey(
        'students.StudentEnrollment',
        on_delete=models.CASCADE,
        related_name='fee_concessions'
    )
    concession = models.ForeignKey(FeeConcession, on_delete=models.CASCADE, related_name='student_assignments')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='assigned_concessions')
    is_active = models.BooleanField(default=True)
    remarks = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_concessions'
    )

    class Meta:
        unique_together = ('student_enrollment', 'concession', 'academic_year')
        verbose_name = _('Student Concession')
        verbose_name_plural = _('Student Concessions')

    def __str__(self):
        return f"{self.student_enrollment.student.full_name} -> {self.concession.name}"


class FeeFineRule(BaseModel):
    """
    Automated Late Fee Rule per Academic Year.
    """
    class FineType(models.TextChoices):
        PER_DAY = 'PER_DAY', _('Per Day Overdue (₹/Day)')
        FLAT = 'FLAT', _('Flat Penalty (₹)')

    name = models.CharField(max_length=100, default='Standard Late Fee Rule')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='fine_rules')
    grace_period_days = models.PositiveIntegerField(default=10, help_text=_('Grace days from issue date before penalty applies'))
    fine_type = models.CharField(max_length=20, choices=FineType.choices, default=FineType.PER_DAY)
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'), help_text=_('₹ per day or flat ₹'))
    max_fine_limit = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1000.00'))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Fee Fine Rule')
        verbose_name_plural = _('Fee Fine Rules')

    def __str__(self):
        return f"{self.name} ({self.academic_year.name}): ₹{self.fine_amount} ({self.get_fine_type_display()})"


class FeeStructure(BaseModel):
    """
    Fee structure rules defined per Grade Level and Academic Year.
    """
    class Frequency(models.TextChoices):
        ONE_TIME = 'ONE_TIME', _('One Time (At Admission)')
        ANNUAL = 'ANNUAL', _('Annual')
        QUARTERLY = 'QUARTERLY', _('Quarterly (Q1, Q2, Q3, Q4)')
        MONTHLY = 'MONTHLY', _('Monthly')

    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='fee_structures')
    class_level = models.ForeignKey('academics.ClassLevel', on_delete=models.CASCADE, related_name='fee_structures')
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='fee_structures')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.QUARTERLY)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['academic_year', 'class_level', 'fee_category']
        unique_together = ('academic_year', 'class_level', 'fee_category', 'frequency')
        verbose_name = _('Fee Structure')
        verbose_name_plural = _('Fee Structures')

    def __str__(self):
        return f"{self.class_level.name} - {self.fee_category.name} (₹{self.amount} {self.get_frequency_display()})"


class StudentFeeInvoice(BaseModel):
    """
    Student Fee Invoice record with itemized heads, late fine calculations, and concession support.
    """
    class Status(models.TextChoices):
        UNPAID = 'UNPAID', _('Unpaid')
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Fully Paid')
        OVERDUE = 'OVERDUE', _('Overdue')
        CANCELLED = 'CANCELLED', _('Cancelled')

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    student_enrollment = models.ForeignKey('students.StudentEnrollment', on_delete=models.CASCADE, related_name='fee_invoices')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='fee_invoices')
    title = models.CharField(max_length=150, help_text=_('e.g. Q1 Tuition & Science Lab Fee'))
    
    issue_date = models.DateField()
    due_date = models.DateField()
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    concession_applied = models.ForeignKey(FeeConcession, on_delete=models.SET_NULL, null=True, blank=True, related_name='applied_invoices')
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']
        verbose_name = _('Student Fee Invoice')
        verbose_name_plural = _('Student Fee Invoices')

    def __str__(self):
        return f"{self.invoice_number} | {self.student_enrollment.student.full_name} ({self.get_status_display()} - ₹{self.balance_amount})"

    @property
    def is_overdue(self):
        return self.status != self.Status.PAID and self.due_date < timezone.now().date()

    @property
    def overdue_days(self):
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0

    @property
    def net_payable(self):
        return max(Decimal('0.00'), (self.total_amount - self.discount_amount) + self.fine_amount)

    def calculate_and_apply_fine(self, fine_rule=None):
        """Auto-computes late fee fine if overdue based on active FeeFineRule."""
        if self.status == self.Status.PAID:
            return self.fine_amount

        if not fine_rule:
            fine_rule = FeeFineRule.objects.filter(academic_year=self.academic_year, is_active=True).first()

        if fine_rule and self.due_date:
            days_late = (timezone.now().date() - self.due_date).days
            if days_late > fine_rule.grace_period_days:
                overdue_count = days_late - fine_rule.grace_period_days
                if fine_rule.fine_type == FeeFineRule.FineType.PER_DAY:
                    calculated = Decimal(overdue_count) * fine_rule.fine_amount
                else:
                    calculated = fine_rule.fine_amount
                self.fine_amount = min(calculated, fine_rule.max_fine_limit)
                self.update_balance()
        return self.fine_amount

    def update_balance(self):
        payments_total = self.payments.filter(is_deleted=False).aggregate(models.Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        self.paid_amount = payments_total
        self.balance_amount = max(Decimal('0.00'), self.net_payable - self.paid_amount)
        
        if self.balance_amount == Decimal('0.00'):
            self.status = self.Status.PAID
        elif self.paid_amount > Decimal('0.00'):
            self.status = self.Status.PARTIAL
        elif self.is_overdue:
            self.status = self.Status.OVERDUE
        else:
            self.status = self.Status.UNPAID
        self.save()


class InvoiceLineItem(BaseModel):
    """
    Individual fee head line item breakdown in an invoice.
    """
    invoice = models.ForeignKey(StudentFeeInvoice, on_delete=models.CASCADE, related_name='line_items')
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='line_items')
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['fee_category__name']
        verbose_name = _('Invoice Line Item')
        verbose_name_plural = _('Invoice Line Items')

    def __str__(self):
        return f"{self.title}: ₹{self.amount}"


class StudentFeePayment(BaseModel):
    """
    Receipt transaction record for fee collection with Indian UPI, Cheque, and POS multi-mode support.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash Counter')
        UPI = 'UPI', _('UPI / QR Code Scan')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer / NEFT / RTGS')
        CHEQUE = 'CHEQUE', _('Cheque / Demand Draft')
        ONLINE = 'ONLINE', _('Online Payment / Parent Portal')
        CARD = 'CARD', _('Debit / Credit Card (POS)')

    invoice = models.ForeignKey(StudentFeeInvoice, on_delete=models.CASCADE, related_name='payments')
    receipt_number = models.CharField(max_length=50, unique=True, db_index=True)
    payment_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    
    # Detailed payment references
    transaction_id = models.CharField(max_length=100, blank=True, help_text=_('Bank UTR or Gateway Transaction Ref'))
    upi_utr_number = models.CharField(max_length=50, blank=True, help_text=_('12-digit UPI UTR Reference'))
    cheque_number = models.CharField(max_length=50, blank=True, help_text=_('Cheque / DD Number'))
    cheque_bank_name = models.CharField(max_length=100, blank=True, help_text=_('Issuing Bank & Branch'))
    cheque_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_fee_payments'
    )

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = _('Fee Payment Receipt')
        verbose_name_plural = _('Fee Payment Receipts')

    def __str__(self):
        return f"{self.receipt_number} | {self.invoice.student_enrollment.student.full_name} (₹{self.amount_paid} via {self.get_payment_method_display()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.update_balance()
