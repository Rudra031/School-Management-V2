from decimal import Decimal
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from academics.models import AcademicYear, ClassLevel, Section, Subject
from students.models import Student, StudentEnrollment
from staff.models import StaffMember
from attendance.models import StudentAttendanceSheet, StudentAttendanceRecord
from examinations.models import ExamTerm, ExamMarkEntry
from fees.models import StudentFeeInvoice, StudentFeePayment
from expenses.models import Expense
from core.permissions import AdminOrPrincipalRequiredMixin, AccountantRequiredMixin, RoleRequiredMixin
from core.utils import export_to_csv, export_to_excel

class ConsolidatedReportsHubView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    Central Executive Intelligence & Reports Hub.
    """
    template_name = 'reports/hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        context['academic_year'] = academic_year
        context['total_students'] = Student.objects.filter(status=Student.Status.ACTIVE, is_deleted=False).count()
        context['total_staff'] = StaffMember.objects.filter(status=StaffMember.Status.ACTIVE, is_deleted=False).count()
        context['total_classes'] = ClassLevel.objects.filter(is_deleted=False).count()
        context['total_sections'] = Section.objects.filter(is_deleted=False).count()
        return context


class StudentDemographicsReportView(AdminOrPrincipalRequiredMixin, TemplateView):
    template_name = 'reports/demographics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        class_rows = []
        for cl in ClassLevel.objects.filter(is_deleted=False):
            enrollments = StudentEnrollment.objects.filter(
                academic_year=academic_year, section__class_level=cl, is_current=True, is_deleted=False
            )
            total = enrollments.count()
            male = enrollments.filter(student__gender='MALE').count()
            female = enrollments.filter(student__gender='FEMALE').count()
            other = total - (male + female)

            class_rows.append({
                'class_level': cl,
                'total': total,
                'male': male,
                'female': female,
                'other': other,
            })

        context['class_rows'] = class_rows
        return context


class FinancialIncomeExpenseReportView(AccountantRequiredMixin, TemplateView):
    """
    Consolidated Profit & Loss, Fee Collections vs Operating Expenses statement.
    """
    template_name = 'reports/financial_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        payments = StudentFeePayment.objects.filter(is_deleted=False)
        expenses = Expense.objects.filter(is_deleted=False)
        if academic_year:
            payments = payments.filter(invoice__academic_year=academic_year)
            expenses = expenses.filter(academic_year=academic_year)

        total_income = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        net_balance = total_income - total_expenses

        context['academic_year'] = academic_year
        context['total_income'] = total_income
        context['total_expenses'] = total_expenses
        context['net_balance'] = net_balance
        context['is_surplus'] = net_balance >= 0
        return context


class FinancialReportExportView(AccountantRequiredMixin, View):
    def get(self, request):
        academic_year = getattr(request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        fmt = request.GET.get('format', 'csv')
        filename = f"financial_pnl_statement_{timezone.now().strftime('%Y%m%d')}"

        payments = StudentFeePayment.objects.filter(is_deleted=False)
        expenses = Expense.objects.filter(is_deleted=False)
        if academic_year:
            payments = payments.filter(invoice__academic_year=academic_year)
            expenses = expenses.filter(academic_year=academic_year)

        total_income = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        net_balance = total_income - total_expenses

        headers = ['Financial Account Line', 'Amount ($)']
        rows = [
            ['Total Fee Collections (Income)', str(total_income)],
            ['Total Operating Expenses (Outflow)', str(total_expenses)],
            ['Net Operating Surplus / (Deficit)', str(net_balance)],
        ]

        if fmt == 'excel':
            return export_to_excel(filename, headers, rows)
        return export_to_csv(filename, headers, rows)
