from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q
from django.contrib import messages

from staff.models import StaffMember, Designation
from staff.forms import StaffMemberCreateForm, StaffMemberUpdateForm, DesignationForm
from academics.models import Department
from core.permissions import AdminOrPrincipalRequiredMixin, SchoolAdminRequiredMixin
from core.utils import log_audit, export_to_csv, export_to_excel
from core.models import AuditLog

class StaffListView(AdminOrPrincipalRequiredMixin, ListView):
    model = StaffMember
    template_name = 'staff/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 25

    def get_queryset(self):
        qs = StaffMember.objects.filter(is_deleted=False).select_related('user', 'designation', 'department')
        search_query = self.request.GET.get('search', '').strip()
        dept = self.request.GET.get('department')
        status = self.request.GET.get('status')
        designation = self.request.GET.get('designation')

        if search_query:
            qs = qs.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(employee_id__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        if dept:
            qs = qs.filter(department_id=dept)
        if status:
            qs = qs.filter(status=status)
        if designation:
            qs = qs.filter(designation_id=designation)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_deleted=False)
        context['designations'] = Designation.objects.filter(is_deleted=False)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_dept'] = self.request.GET.get('department', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_designation'] = self.request.GET.get('designation', '')
        return context


class StaffDetailView(AdminOrPrincipalRequiredMixin, DetailView):
    model = StaffMember
    template_name = 'staff/staff_detail.html'
    context_object_name = 'staff'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allocations'] = self.object.subject_allocations.filter(is_deleted=False).select_related('section__class_level', 'subject', 'academic_year')
        context['assigned_sections'] = self.object.assigned_class_sections.filter(is_deleted=False).select_related('class_level')
        return context


class StaffCreateView(SchoolAdminRequiredMixin, CreateView):
    model = StaffMember
    form_class = StaffMemberCreateForm
    template_name = 'staff/staff_form.html'
    success_url = reverse_lazy('staff:staff_list')

    def form_valid(self, form):
        messages.success(self.request, f"Staff member '{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}' created successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Staff',
            model_name='StaffMember',
            object_id=str(self.object.id),
            object_repr=self.object.full_name
        )
        return response


class StaffUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberUpdateForm
    template_name = 'staff/staff_form.html'

    def get_success_url(self):
        return reverse_lazy('staff:staff_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Staff record '{self.object.full_name}' updated successfully.")
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Staff',
            model_name='StaffMember',
            object_id=str(self.object.id),
            object_repr=self.object.full_name,
            changes={'updated_fields': list(form.changed_data)}
        )
        return super().form_valid(form)


class StaffExportView(AdminOrPrincipalRequiredMixin, View):
    def get(self, request):
        export_type = request.GET.get('format', 'excel')
        staff_qs = StaffMember.objects.filter(is_deleted=False).select_related('designation', 'department', 'user')

        headers = ['Employee ID', 'Full Name', 'Email', 'Designation', 'Department', 'Gender', 'Joining Date', 'Status', 'Phone']
        rows = [
            [
                s.employee_id,
                s.full_name,
                s.email,
                s.designation.title,
                s.department.name if s.department else 'N/A',
                s.get_gender_display(),
                s.joining_date.strftime('%Y-%m-%d'),
                s.get_status_display(),
                s.user.phone_number if s.user else ''
            ]
            for s in staff_qs
        ]

        if export_type == 'csv':
            return export_to_csv('staff_directory', headers, rows)
        return export_to_excel('staff_directory', 'Staff Directory', headers, rows)


import uuid
from decimal import Decimal
from django.views.generic import TemplateView
from django.utils import timezone
from staff.models import SalaryStructure, PayrollPeriod, StaffSalarySlip
from staff.forms import SalaryStructureForm, PayrollBatchGenerateForm, StaffSalarySlipUpdateForm
from academics.models import AcademicYear
from core.permissions import AccountantRequiredMixin


class PayrollDashboardView(AccountantRequiredMixin, TemplateView):
    """
    Central HR & Payroll Operations Hub.
    """
    template_name = 'staff/payroll/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        
        periods = PayrollPeriod.objects.filter(is_deleted=False).select_related('academic_year', 'generated_by')
        if academic_year:
            periods = periods.filter(academic_year=academic_year)
            
        staff_members = StaffMember.objects.filter(status=StaffMember.Status.ACTIVE, is_deleted=False).select_related('salary_structure', 'designation', 'department')
        
        total_payroll_disbursed = sum(p.total_disbursed for p in periods.filter(status=PayrollPeriod.Status.PAID))
        active_staff_count = staff_members.count()
        configured_structures_count = sum(1 for s in staff_members if hasattr(s, 'salary_structure'))
        
        context['academic_year'] = academic_year
        context['payroll_periods'] = periods
        context['staff_members'] = staff_members
        context['total_payroll_disbursed'] = total_payroll_disbursed
        context['active_staff_count'] = active_staff_count
        context['configured_structures_count'] = configured_structures_count
        return context


class PayrollPeriodDetailView(AccountantRequiredMixin, DetailView):
    """
    Detailed summary of all staff salary slips within a specific monthly payroll cycle.
    """
    model = PayrollPeriod
    template_name = 'staff/payroll/period_detail.html'
    context_object_name = 'payroll_period'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slips = self.object.salary_slips.filter(is_deleted=False).select_related('staff_member__designation', 'staff_member__department')
        
        total_gross = sum(s.gross_salary for s in slips)
        total_deductions = sum(s.total_deductions for s in slips)
        total_net = sum(s.net_salary for s in slips)
        
        context['slips'] = slips
        context['total_gross'] = total_gross
        context['total_deductions'] = total_deductions
        context['total_net'] = total_net
        return context


class PayrollBatchGenerateView(AccountantRequiredMixin, View):
    """
    Executes automated monthly payroll generation across all active staff.
    """
    template_name = 'staff/payroll/batch_generate.html'

    def get(self, request):
        academic_year = getattr(request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        now = timezone.now()
        form = PayrollBatchGenerateForm(initial={
            'academic_year': academic_year,
            'month': now.month,
            'year': now.year,
            'payment_date': now.date(),
        })
        return render(request, self.template_name, {'form': form, 'academic_year': academic_year})

    def post(self, request):
        form = PayrollBatchGenerateForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        academic_year = form.cleaned_data['academic_year']
        month = int(form.cleaned_data['month'])
        year = int(form.cleaned_data['year'])
        payment_date = form.cleaned_data['payment_date']
        default_method = form.cleaned_data['payment_method']
        notes = form.cleaned_data.get('notes', '')

        # Check if period already exists
        period, created = PayrollPeriod.objects.get_or_create(
            academic_year=academic_year,
            month=month,
            year=year,
            defaults={
                'payment_date': payment_date,
                'status': PayrollPeriod.Status.GENERATED,
                'generated_by': request.user,
                'notes': notes,
            }
        )

        active_staff = StaffMember.objects.filter(status=StaffMember.Status.ACTIVE, is_deleted=False)
        generated_count = 0

        for staff in active_staff:
            # Check or create default salary structure
            struct = getattr(staff, 'salary_structure', None)
            if not struct:
                struct = SalaryStructure.objects.create(
                    staff_member=staff,
                    basic_salary=staff.basic_salary or Decimal('3500.00'),
                    house_rent_allowance=Decimal('500.00'),
                    transport_allowance=Decimal('200.00'),
                    medical_allowance=Decimal('150.00'),
                    special_allowance=Decimal('100.00'),
                    tax_deduction=Decimal('200.00'),
                    provident_fund=Decimal('150.00'),
                    insurance_deduction=Decimal('50.00'),
                )

            slip_num = f"PAY-{year}-{month:02d}-{staff.employee_id}"
            slip, s_created = StaffSalarySlip.objects.update_or_create(
                payroll_period=period,
                staff_member=staff,
                defaults={
                    'slip_number': slip_num,
                    'basic_salary': struct.basic_salary,
                    'allowance_hra': struct.house_rent_allowance,
                    'allowance_transport': struct.transport_allowance,
                    'allowance_medical': struct.medical_allowance,
                    'allowance_special': struct.special_allowance,
                    'incentives_bonus': Decimal('0.00'),
                    'deduction_tax': struct.tax_deduction,
                    'deduction_pf': struct.provident_fund,
                    'deduction_insurance': struct.insurance_deduction,
                    'deduction_leave_penalty': Decimal('0.00'),
                    'deduction_other': struct.other_deductions,
                    'gross_salary': struct.gross_salary,
                    'total_deductions': struct.total_deductions,
                    'net_salary': struct.net_salary,
                    'payment_method': default_method,
                    'payment_status': StaffSalarySlip.PaymentStatus.PAID,
                    'transaction_reference': f"TXN-SAL-{uuid.uuid4().hex[:8].upper()}",
                    'payment_date': payment_date,
                }
            )
            generated_count += 1

        period.status = PayrollPeriod.Status.GENERATED
        period.update_totals()

        messages.success(request, f"Successfully generated {generated_count} salary slips for {period.get_month_display()} {year} (Total: ${period.total_disbursed:,.2f}).")
        log_audit(
            request,
            action=AuditLog.Action.CREATE,
            module='Payroll',
            model_name='PayrollPeriod',
            object_id=str(period.id),
            object_repr=str(period)
        )
        return redirect('staff:payroll_period_detail', pk=period.pk)


class PayrollPeriodApproveView(AccountantRequiredMixin, View):
    def post(self, request, pk):
        period = get_object_or_404(PayrollPeriod, pk=pk, is_deleted=False)
        period.status = PayrollPeriod.Status.APPROVED
        period.save()
        messages.success(request, f"Payroll for {period.get_month_display()} {period.year} has been approved.")
        return redirect('staff:payroll_period_detail', pk=period.pk)


class PayrollPeriodDisburseView(AccountantRequiredMixin, View):
    def post(self, request, pk):
        period = get_object_or_404(PayrollPeriod, pk=pk, is_deleted=False)
        period.status = PayrollPeriod.Status.PAID
        period.salary_slips.filter(is_deleted=False).update(
            payment_status=StaffSalarySlip.PaymentStatus.PAID,
            payment_date=timezone.now().date()
        )
        period.save()
        messages.success(request, f"Payroll for {period.get_month_display()} {period.year} has been marked as fully disbursed.")
        return redirect('staff:payroll_period_detail', pk=period.pk)


class SalarySlipDetailView(AccountantRequiredMixin, DetailView):
    model = StaffSalarySlip
    template_name = 'staff/payroll/salary_slip_detail.html'
    context_object_name = 'slip'


class SalarySlipPrintView(AccountantRequiredMixin, DetailView):
    model = StaffSalarySlip
    template_name = 'staff/payroll/salary_slip_print.html'
    context_object_name = 'slip'


class StaffSalaryStructureUpdateView(AccountantRequiredMixin, View):
    template_name = 'staff/payroll/salary_structure_form.html'

    def get(self, request, pk):
        staff = get_object_or_404(StaffMember, pk=pk, is_deleted=False)
        structure, _ = SalaryStructure.objects.get_or_create(
            staff_member=staff,
            defaults={'basic_salary': staff.basic_salary or Decimal('3500.00')}
        )
        form = SalaryStructureForm(instance=structure)
        return render(request, self.template_name, {'form': form, 'staff': staff, 'structure': structure})

    def post(self, request, pk):
        staff = get_object_or_404(StaffMember, pk=pk, is_deleted=False)
        structure, _ = SalaryStructure.objects.get_or_create(
            staff_member=staff,
            defaults={'basic_salary': staff.basic_salary or Decimal('3500.00')}
        )
        form = SalaryStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            # Also update staff basic salary
            staff.basic_salary = form.cleaned_data['basic_salary']
            staff.save(update_fields=['basic_salary'])
            messages.success(request, f"Salary structure for {staff.full_name} updated successfully.")
            return redirect('staff:payroll_dashboard')
        return render(request, self.template_name, {'form': form, 'staff': staff, 'structure': structure})

