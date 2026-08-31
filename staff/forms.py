from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from accounts.models import User, UserRole
from staff.models import StaffMember, Designation
from academics.models import Department

class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ['title', 'department', 'is_teaching_role', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior PGT Mathematics'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'is_teaching_role': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StaffMemberCreateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'teacher@school.edu'}),
        label=_('Email Address (Login Username)')
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••', 'id': 'id_password'}),
        initial='Teacher@2026!',
        help_text=_('Initial password for faculty portal access.')
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current residential address'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'id_avatar'}),
        label=_('Profile Photograph')
    )
    must_change_password = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        label=_('Force password change on first login')
    )

    class Meta:
        model = StaffMember
        fields = [
            'employee_id', 'designation', 'department', 'first_name', 'last_name',
            'gender', 'date_of_birth', 'national_id_number', 'qualification',
            'experience_years', 'joining_date', 'basic_salary', 'contract_type',
            'blood_group', 'marital_status', 'emergency_contact_name', 'emergency_contact_phone',
            'resume_file'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. FAC-2026-0101', 'id': 'id_employee_id'}),
            'designation': forms.Select(attrs={'class': 'form-select', 'id': 'id_designation'}),
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_first_name', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_last_name', 'placeholder': 'Last Name'}),
            'gender': forms.Select(attrs={'class': 'form-select', 'id': 'id_gender'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SSN / National ID'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_qualification', 'placeholder': 'e.g. M.Sc. Mathematics, B.Ed.'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_experience_years', 'min': '0'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_joining_date'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'contract_type': forms.Select(attrs={'class': 'form-select'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary contact name'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency phone number'}),
            'resume_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user account with this email address already exists.'))
        return email

    def clean_employee_id(self):
        emp_id = self.cleaned_data.get('employee_id', '').strip()
        if StaffMember.objects.filter(employee_id=emp_id).exists():
            raise forms.ValidationError(_('A staff member with this Employee ID already exists.'))
        return emp_id

    @transaction.atomic
    def save(self, commit=True):
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        phone = self.cleaned_data.get('phone_number', '')
        address = self.cleaned_data.get('address', '')
        avatar = self.cleaned_data.get('avatar')
        must_change = self.cleaned_data.get('must_change_password', True)
        designation = self.cleaned_data['designation']
        
        # Determine appropriate User role (Teacher vs Support Staff)
        role = UserRole.TEACHER if designation.is_teaching_role else UserRole.STAFF
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            user_type=role,
            phone_number=phone,
            address=address,
            avatar=avatar,
            must_change_password=must_change
        )

        staff_member = super().save(commit=False)
        staff_member.user = user
        if commit:
            staff_member.save()
        return staff_member


class StaffMemberUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = StaffMember
        fields = [
            'designation', 'department', 'first_name', 'last_name',
            'gender', 'date_of_birth', 'national_id_number', 'qualification',
            'experience_years', 'joining_date', 'basic_salary', 'contract_type',
            'status', 'blood_group', 'marital_status',
            'emergency_contact_name', 'emergency_contact_phone', 'resume_file'
        ]
        widgets = {
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'national_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contract_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'resume_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['address'].initial = self.instance.user.address

    @transaction.atomic
    def save(self, commit=True):
        staff = super().save(commit=False)
        if staff.user:
            user = staff.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.phone_number = self.cleaned_data.get('phone_number', '')
            user.address = self.cleaned_data.get('address', '')
            if self.cleaned_data.get('avatar'):
                user.avatar = self.cleaned_data['avatar']
            
            # Update user role if designation changed
            if 'designation' in self.cleaned_data:
                role = UserRole.TEACHER if self.cleaned_data['designation'].is_teaching_role else UserRole.STAFF
                user.user_type = role
            user.save()
        if commit:
            staff.save()
        return staff


from staff.models import SalaryStructure, PayrollPeriod, StaffSalarySlip
from academics.models import AcademicYear


class SalaryStructureForm(forms.ModelForm):
    class Meta:
        model = SalaryStructure
        fields = [
            'basic_salary',
            'house_rent_allowance', 'transport_allowance', 'medical_allowance', 'special_allowance',
            'tax_deduction', 'provident_fund', 'insurance_deduction', 'other_deductions',
            'bank_name', 'account_number', 'bank_branch'
        ]
        widgets = {
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'house_rent_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'transport_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'medical_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'special_allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'provident_fund': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. JPMorgan Chase'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '•••• •••• •••• 1234'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Downtown Central'}),
        }


class PayrollBatchGenerateForm(forms.Form):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Academic Year')
    )
    month = forms.ChoiceField(
        choices=PayrollPeriod.Month.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Payroll Month')
    )
    year = forms.IntegerField(
        initial=2026,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label=_('Payroll Year')
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('Disbursement / Payment Date')
    )
    payment_method = forms.ChoiceField(
        choices=StaffSalarySlip.PaymentMethod.choices,
        initial=StaffSalarySlip.PaymentMethod.BANK_TRANSFER,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Default Payment Method')
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional internal notes...'}),
        label=_('Payroll Run Notes')
    )


class StaffSalarySlipUpdateForm(forms.ModelForm):
    class Meta:
        model = StaffSalarySlip
        fields = [
            'basic_salary', 'allowance_hra', 'allowance_transport', 'allowance_medical',
            'allowance_special', 'incentives_bonus',
            'deduction_tax', 'deduction_pf', 'deduction_insurance', 'deduction_leave_penalty', 'deduction_other',
            'payment_method', 'payment_status', 'transaction_reference', 'payment_date', 'remarks'
        ]
        widgets = {
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowance_hra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowance_transport': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowance_medical': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowance_special': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'incentives_bonus': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deduction_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deduction_pf': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deduction_insurance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deduction_leave_penalty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deduction_other': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

