import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class Designation(BaseModel):
    """
    Staff / Faculty Job Designation (e.g. Principal, Vice Principal, PGT Mathematics, Lab Assistant).
    """
    title = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='designations'
    )
    is_teaching_role = models.BooleanField(default=True, help_text=_('Identifies if this designation teaches classes'))
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['title']
        verbose_name = _('Designation')
        verbose_name_plural = _('Designations')

    def __str__(self):
        return self.title


class StaffMember(BaseModel):
    """
    Staff / Employee Profile linked 1-to-1 to a User account.
    """
    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    class ContractType(models.TextChoices):
        PERMANENT = 'PERMANENT', _('Permanent')
        PROBATION = 'PROBATION', _('Probation')
        CONTRACT = 'CONTRACT', _('Contractual')
        VISITING = 'VISITING', _('Visiting Faculty')

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        ON_LEAVE = 'ON_LEAVE', _('On Leave')
        RESIGNED = 'RESIGNED', _('Resigned')
        TERMINATED = 'TERMINATED', _('Terminated')
        RETIRED = 'RETIRED', _('Retired')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True, db_index=True)
    designation = models.ForeignKey(Designation, on_delete=models.PROTECT, related_name='staff_members')
    department = models.ForeignKey(
        'academics.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members'
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id_number = models.CharField(max_length=100, blank=True, help_text=_('SSN / National ID'))
    qualification = models.CharField(max_length=200, help_text=_('e.g. M.Sc. Mathematics, B.Ed.'))
    experience_years = models.PositiveSmallIntegerField(default=0)
    joining_date = models.DateField()
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True)
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-')
        ],
        blank=True
    )
    marital_status = models.CharField(
        max_length=20,
        choices=[('SINGLE', 'Single'), ('MARRIED', 'Married'), ('DIVORCED', 'Divorced'), ('WIDOWED', 'Widowed')],
        blank=True
    )
    
    # Employment Details
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.PERMANENT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    resume_file = models.FileField(upload_to='staff/resumes/', blank=True, null=True)

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = _('Staff Member')
        verbose_name_plural = _('Staff Members')
        indexes = [
            models.Index(fields=['employee_id', 'status']),
            models.Index(fields=['department', 'status']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id}) - {self.designation.title}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def email(self):
        return self.user.email if self.user else ''

from decimal import Decimal
from django.utils import timezone


class SalaryStructure(BaseModel):
    """
    Staff Compensation & Salary Structure Configuration.
    Formula: Basic Salary + Allowances - Deductions = Net Salary.
    """
    staff_member = models.OneToOneField(
        StaffMember,
        on_delete=models.CASCADE,
        related_name='salary_structure'
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('3500.00'))
    
    # Allowances
    house_rent_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'), help_text=_('HRA Allowance'))
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'), help_text=_('Travel/Conveyance Allowance'))
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('150.00'), help_text=_('Medical Support Allowance'))
    special_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'), help_text=_('Special/Academic Incentive'))
    
    # Deductions
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'), help_text=_('Income Tax / TDS'))
    provident_fund = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('150.00'), help_text=_('PF / Retirement Contribution'))
    insurance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'), help_text=_('Health/Life Insurance Premium'))
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text=_('Miscellaneous Deductions'))
    
    # Bank & Payment Info
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = _('Salary Structure')
        verbose_name_plural = _('Salary Structures')

    def __str__(self):
        return f"{self.staff_member.full_name} Structure (Net: ${self.net_salary})"

    @property
    def total_allowances(self):
        return self.house_rent_allowance + self.transport_allowance + self.medical_allowance + self.special_allowance

    @property
    def total_deductions(self):
        return self.tax_deduction + self.provident_fund + self.insurance_deduction + self.other_deductions

    @property
    def gross_salary(self):
        return self.basic_salary + self.total_allowances

    @property
    def net_salary(self):
        return max(Decimal('0.00'), self.gross_salary - self.total_deductions)


class PayrollPeriod(BaseModel):
    """
    Monthly Institutional Payroll Run Cycle.
    """
    class Month(models.IntegerChoices):
        JANUARY = 1, _('January')
        FEBRUARY = 2, _('February')
        MARCH = 3, _('March')
        APRIL = 4, _('April')
        MAY = 5, _('May')
        JUNE = 6, _('June')
        JULY = 7, _('July')
        AUGUST = 8, _('August')
        SEPTEMBER = 9, _('September')
        OCTOBER = 10, _('October')
        NOVEMBER = 11, _('November')
        DECEMBER = 12, _('December')

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft In Progress')
        GENERATED = 'GENERATED', _('Generated & Verified')
        APPROVED = 'APPROVED', _('Approved by Principal')
        PAID = 'PAID', _('Disbursed & Completed')

    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.CASCADE,
        related_name='payroll_periods'
    )
    month = models.PositiveSmallIntegerField(choices=Month.choices, default=Month.JANUARY)
    year = models.PositiveIntegerField(default=2026)
    payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    total_disbursed = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_payrolls'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ('academic_year', 'month', 'year')
        verbose_name = _('Payroll Period')
        verbose_name_plural = _('Payroll Periods')

    def __str__(self):
        return f"Payroll {self.get_month_display()} {self.year} ({self.get_status_display()})"

    @property
    def total_employees(self):
        return self.salary_slips.count()

    def update_totals(self):
        slips = self.salary_slips.filter(is_deleted=False)
        self.total_disbursed = sum(s.net_salary for s in slips)
        self.save()


class StaffSalarySlip(BaseModel):
    """
    Individual Monthly Staff Pay Stub / Salary Slip.
    """
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', _('Direct Bank Deposit / Wire')
        CHEQUE = 'CHEQUE', _('Company Cheque')
        CASH = 'CASH', _('Cash Disbursement')
        ONLINE = 'ONLINE', _('Corporate UPI / Digital')

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Processing')
        PAID = 'PAID', _('Disbursed / Paid')
        CANCELLED = 'CANCELLED', _('Cancelled / Reversed')

    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='salary_slips'
    )
    staff_member = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name='salary_slips'
    )
    slip_number = models.CharField(max_length=60, unique=True, db_index=True)
    
    # Itemized Breakdown
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowance_hra = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    allowance_transport = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    allowance_medical = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    allowance_special = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    incentives_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    deduction_tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deduction_pf = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deduction_insurance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deduction_leave_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deduction_other = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PAID)
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField(default=timezone.now)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['staff_member__employee_id']
        unique_together = ('payroll_period', 'staff_member')
        verbose_name = _('Staff Salary Slip')
        verbose_name_plural = _('Staff Salary Slips')

    def __str__(self):
        return f"{self.slip_number} | {self.staff_member.full_name} (${self.net_salary})"

    @property
    def total_allowances(self):
        return self.allowance_hra + self.allowance_transport + self.allowance_medical + self.allowance_special + self.incentives_bonus

    def save(self, *args, **kwargs):
        if not self.gross_salary:
            self.gross_salary = self.basic_salary + self.total_allowances
        if not self.total_deductions:
            self.total_deductions = (
                self.deduction_tax + self.deduction_pf + self.deduction_insurance +
                self.deduction_leave_penalty + self.deduction_other
            )
        if not self.net_salary:
            self.net_salary = max(Decimal('0.00'), self.gross_salary - self.total_deductions)
        super().save(*args, **kwargs)
        self.payroll_period.update_totals()
