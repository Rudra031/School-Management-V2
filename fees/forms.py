from decimal import Decimal
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from fees.models import FeeCategory, FeeStructure, StudentFeeInvoice, StudentFeePayment, FeeConcession, StudentConcession, FeeFineRule
from academics.models import AcademicYear, ClassLevel, Section
from students.models import StudentEnrollment

class FeeCategoryForm(forms.ModelForm):
    class Meta:
        model = FeeCategory
        fields = ['name', 'category_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tuition Fee'}),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FeeConcessionForm(forms.ModelForm):
    class Meta:
        model = FeeConcession
        fields = ['name', 'code', 'concession_type', 'discount_value', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sibling Discount (20%)'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SIBLING_20'}),
            'concession_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '20.00'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StudentConcessionAssignForm(forms.ModelForm):
    class Meta:
        model = StudentConcession
        fields = ['student_enrollment', 'concession', 'academic_year', 'remarks', 'is_active']
        widgets = {
            'student_enrollment': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'concession': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Approved per parent document'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeeFineRuleForm(forms.ModelForm):
    class Meta:
        model = FeeFineRule
        fields = ['name', 'academic_year', 'grace_period_days', 'fine_type', 'fine_amount', 'max_fine_limit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard 10-Day Grace Rule'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'fine_type': forms.Select(attrs={'class': 'form-select'}),
            'fine_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_fine_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['academic_year', 'class_level', 'fee_category', 'amount', 'frequency', 'due_date']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'class_level': forms.Select(attrs={'class': 'form-select'}),
            'fee_category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class StudentFeeInvoiceForm(forms.ModelForm):
    class Meta:
        model = StudentFeeInvoice
        fields = ['academic_year', 'student_enrollment', 'title', 'issue_date', 'due_date', 'total_amount', 'discount_amount', 'concession_applied', 'fine_amount', 'remarks']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'student_enrollment': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q1 Tuition & Lab Invoice'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'concession_applied': forms.Select(attrs={'class': 'form-select'}),
            'fine_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StudentFeePaymentForm(forms.ModelForm):
    class Meta:
        model = StudentFeePayment
        fields = ['payment_date', 'amount_paid', 'payment_method', 'transaction_id', 'upi_utr_number', 'cheque_number', 'cheque_bank_name', 'cheque_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank / UTR Reference'}),
            'upi_utr_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12-digit UPI UTR'}),
            'cheque_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cheque / DD #'}),
            'cheque_bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank & Branch Name'}),
            'cheque_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Payment notes / Cashier remarks'}),
        }


class InvoiceBatchGenerationForm(forms.Form):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Academic Session'
    )
    class_level = forms.ModelChoiceField(
        queryset=ClassLevel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Target Class Level'
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Section (Optional - Leave blank for all sections in class)'
    )
    fee_category = forms.ModelChoiceField(
        queryset=FeeCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Fee Category'
    )
    title = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q1 Tuition & Lab Fee 2026-27'}),
        label='Invoice Title'
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Fee Amount Per Student (₹)'
    )
    due_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Payment Due Date'
    )

