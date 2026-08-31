from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import FormView, UpdateView, TemplateView, ListView, CreateView, DeleteView
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from accounts.models import User, UserRole
from accounts.forms import (
    UserLoginForm,
    UserProfileForm,
    CustomPasswordChangeForm,
    ManualUserCreationForm,
    ManualUserUpdateForm,
    AdminPasswordResetForm,
)
from core.models import AuditLog
from core.utils import log_audit
from core.permissions import (
    RoleRequiredMixin,
    SuperAdminRequiredMixin,
    PrincipalRequiredMixin,
    SchoolAdminRequiredMixin,
    AdminOrPrincipalRequiredMixin,
    TeacherRequiredMixin,
    AccountantRequiredMixin,
    LibrarianRequiredMixin,
    StudentRequiredMixin,
    ParentRequiredMixin,
    StaffRequiredMixin,
)

class UserLoginView(FormView):
    """
    Handles secure user login with audit logging and remember-me session management.
    """
    template_name = 'accounts/login.html'
    form_class = UserLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard_router')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        remember_me = form.cleaned_data.get('remember_me')
        
        login(self.request, user)
        
        # Session duration configuration
        if remember_me:
            self.request.session.set_expiry(60 * 60 * 24 * 30) # 30 days
        else:
            self.request.session.set_expiry(0) # Browser close

        # Update last login IP
        user.last_login_ip = getattr(self.request, 'client_ip', None)
        user.save(update_fields=['last_login_ip'])

        # Mark session for login splash screen
        self.request.session['just_logged_in'] = True

        # Audit Log
        log_audit(
            self.request,
            action=AuditLog.Action.LOGIN,
            module='Authentication',
            model_name='User',
            object_id=str(user.id),
            object_repr=user.email,
            changes={'event': 'User authenticated successfully'}
        )

        messages.success(self.request, f"Welcome back, {user.full_name}!")
        
        next_url = self.request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('accounts:dashboard_router')


class UserLogoutView(View):
    """
    Handles user logout, clears session and records audit event.
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_audit(
                request,
                action=AuditLog.Action.LOGOUT,
                module='Authentication',
                model_name='User',
                object_id=str(request.user.id),
                object_repr=request.user.email,
                changes={'event': 'User logged out'}
            )
            logout(request)
            messages.info(request, "You have been securely logged out.")
        return redirect('accounts:login')

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class DashboardRouterView(LoginRequiredMixin, View):
    """
    Intelligent routing hub that dispatches users to their dedicated persona dashboard.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        role_routes = {
            UserRole.SUPERADMIN: 'accounts:admin_dashboard',
            UserRole.PRINCIPAL: 'accounts:principal_dashboard',
            UserRole.ADMIN: 'accounts:admin_dashboard',
            UserRole.TEACHER: 'accounts:teacher_dashboard',
            UserRole.ACCOUNTANT: 'accounts:accountant_dashboard',
            UserRole.LIBRARIAN: 'accounts:librarian_dashboard',
            UserRole.STUDENT: 'accounts:student_dashboard',
            UserRole.PARENT: 'accounts:parent_dashboard',
            UserRole.STAFF: 'accounts:staff_dashboard',
        }
        target_route = role_routes.get(user.user_type, 'accounts:admin_dashboard')
        return redirect(target_route)


class UserProfileView(LoginRequiredMixin, UpdateView):
    """
    Allows authenticated users to view and edit their profile details.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been successfully updated.")
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Accounts',
            model_name='User',
            object_id=str(self.request.user.id),
            object_repr=self.request.user.email,
            changes={'updated_fields': list(form.changed_data)}
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_activities'] = AuditLog.objects.filter(user=self.request.user)[:10]
        return context


class UserPasswordChangeView(LoginRequiredMixin, FormView):
    """
    Provides secure password change functionality with session re-authentication.
    """
    template_name = 'accounts/change_password.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('accounts:profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Your password was successfully updated!")
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Accounts',
            model_name='User',
            object_id=str(user.id),
            object_repr=user.email,
            changes={'event': 'Password changed'}
        )
        return super().form_valid(form)


# ==============================================================================
# Manual User Management Views (Create, List, Edit, Reset Password, Deactivate)
# ==============================================================================

class UserListView(AdminOrPrincipalRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        query = self.request.GET.get('q')
        role = self.request.GET.get('role')
        status = self.request.GET.get('status')

        if query:
            query = query.strip()
            qs = qs.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone_number__icontains=query)
            )
        if role:
            qs = qs.filter(user_type=role)
        if status:
            if status == 'active':
                qs = qs.filter(is_active=True)
            elif status == 'inactive':
                qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_users = User.objects.all()
        context.update({
            'total_users': all_users.count(),
            'total_active': all_users.filter(is_active=True).count(),
            'total_inactive': all_users.filter(is_active=False).count(),
            'roles': UserRole.choices,
            'selected_role': self.request.GET.get('role', ''),
            'selected_status': self.request.GET.get('status', ''),
            'search_query': self.request.GET.get('q', ''),
        })
        return context


class UserCreateView(AdminOrPrincipalRequiredMixin, FormView):
    template_name = 'accounts/user_form.html'
    form_class = ManualUserCreationForm
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.models import Student
        context['available_students'] = Student.objects.filter(
            is_deleted=False, 
            status=Student.Status.ACTIVE
        ).order_by('first_name', 'last_name')
        context['linked_student_ids'] = []
        return context

    def form_valid(self, form):
        user = form.save()
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Accounts',
            model_name='User',
            object_id=str(user.id),
            object_repr=f"{user.username} ({user.email})",
            changes={'role': user.user_type, 'username': user.username, 'email': user.email}
        )
        messages.success(
            self.request,
            f"User '{user.full_name}' (User ID: {user.username}) successfully created with role {user.get_user_type_display()}!"
        )
        return super().form_valid(form)


class UserUpdateView(AdminOrPrincipalRequiredMixin, UpdateView):
    model = User
    form_class = ManualUserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.models import Student
        context['available_students'] = Student.objects.filter(
            is_deleted=False, 
            status=Student.Status.ACTIVE
        ).order_by('first_name', 'last_name')
        linked_ids = []
        if hasattr(self.object, 'parent_profile'):
            linked_ids = list(self.object.parent_profile.linked_students.values_list('student_id', flat=True))
        context['linked_student_ids'] = linked_ids
        return context

    def form_valid(self, form):
        user = form.save()
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Accounts',
            model_name='User',
            object_id=str(user.id),
            object_repr=f"{user.username} ({user.email})",
            changes={'updated_fields': list(form.changed_data)}
        )
        messages.success(self.request, f"User details for '{user.full_name}' (User ID: {user.username}) updated.")
        return super().form_valid(form)


class UserPasswordResetByAdminView(AdminOrPrincipalRequiredMixin, FormView):
    template_name = 'accounts/user_reset_password.html'
    form_class = AdminPasswordResetForm
    success_url = reverse_lazy('accounts:user_list')

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(User, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = self.target_user
        return context

    def form_valid(self, form):
        new_password = form.cleaned_data['new_password']
        must_change = form.cleaned_data['must_change_password']
        self.target_user.set_password(new_password)
        self.target_user.must_change_password = must_change
        self.target_user.save(update_fields=['password', 'must_change_password'])

        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Accounts',
            model_name='User',
            object_id=str(self.target_user.id),
            object_repr=self.target_user.email,
            changes={'event': 'Password manually assigned by admin', 'must_change_password': must_change}
        )
        messages.success(
            self.request,
            f"Password for user '{self.target_user.full_name}' (User ID: {self.target_user.username}) has been updated successfully!"
        )
        return super().form_valid(form)


class UserToggleActiveView(AdminOrPrincipalRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "You cannot deactivate your own active session.")
            return redirect('accounts:user_list')

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        state = "activated" if user.is_active else "deactivated"
        log_audit(
            request,
            action=AuditLog.Action.STATUS_CHANGE,
            module='Accounts',
            model_name='User',
            object_id=str(user.id),
            object_repr=user.email,
            changes={'is_active': user.is_active}
        )
        messages.success(request, f"User account for '{user.full_name}' has been {state}.")
        return redirect('accounts:user_list')



# ==============================================================================
# Role-Specific Dashboard Views with Chart.js & Heuristic Analytics
# ==============================================================================
import json
from decimal import Decimal
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from academics.models import AcademicYear, ClassLevel, Section, Subject
from students.models import Student, StudentEnrollment
from staff.models import StaffMember
from attendance.models import StudentAttendanceSheet, StudentAttendanceRecord, StaffAttendanceRecord
from examinations.models import ExamTerm, ExamSchedule, ExamMarkEntry
from timetable.models import ClassTimetable, TimeSlot
from assignments.models import Assignment, AssignmentSubmission
from fees.models import StudentFeeInvoice, StudentFeePayment
from library.models import Book, BookCategory, BookCirculation
from admissions.models import AdmissionsApplication
from leave.models import LeaveRequest
from inventory.models import InventoryItem, AssetAllocation
from expenses.models import Expense, ExpenseCategory
from communication.models import Notice, InAppNotification


class AdminDashboardView(SchoolAdminRequiredMixin, TemplateView):
    template_name = 'dashboards/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        # 1. Student Card Metrics
        all_students_qs = Student.objects.filter(is_deleted=False)
        total_students = all_students_qs.filter(status=Student.Status.ACTIVE).count()
        male_students = all_students_qs.filter(gender='MALE', status=Student.Status.ACTIVE).count()
        female_students = all_students_qs.filter(gender='FEMALE', status=Student.Status.ACTIVE).count()
        new_admissions = all_students_qs.filter(
            admission_date__gte=today.replace(month=1, day=1)
        ).count()

        # 2. Teacher Card Metrics
        teachers_qs = StaffMember.objects.filter(designation__is_teaching_role=True, is_deleted=False)
        if not teachers_qs.exists():
            teachers_qs = StaffMember.objects.filter(user__user_type=UserRole.TEACHER, is_deleted=False)
        total_teachers = teachers_qs.count()
        active_teachers = teachers_qs.filter(status=StaffMember.Status.ACTIVE).count()
        teachers_on_leave = LeaveRequest.objects.filter(
            user__user_type=UserRole.TEACHER,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
            is_deleted=False
        ).count()

        # 3. Staff Card Metrics
        staff_qs = StaffMember.objects.filter(is_deleted=False)
        total_staff = staff_qs.count()
        staff_present_today = StaffAttendanceRecord.objects.filter(date=today, status=StaffAttendanceRecord.Status.PRESENT, is_deleted=False).count()
        staff_absent_today = StaffAttendanceRecord.objects.filter(date=today, status=StaffAttendanceRecord.Status.ABSENT, is_deleted=False).count()
        staff_attendance_pct = round((staff_present_today / total_staff * 100), 1) if total_staff > 0 else 0.0

        # 4. Class Card Metrics
        total_classes = ClassLevel.objects.filter(is_deleted=False).count()
        total_sections = Section.objects.filter(is_deleted=False).count()

        # 5. Attendance Card Metrics
        today_sheets = StudentAttendanceSheet.objects.filter(date=today, is_deleted=False)
        student_present_today = StudentAttendanceRecord.objects.filter(sheet__in=today_sheets, status=StudentAttendanceRecord.Status.PRESENT).count()
        student_absent_today = StudentAttendanceRecord.objects.filter(sheet__in=today_sheets, status=StudentAttendanceRecord.Status.ABSENT).count()
        student_late_today = StudentAttendanceRecord.objects.filter(sheet__in=today_sheets, status=StudentAttendanceRecord.Status.LATE).count()
        total_records_today = StudentAttendanceRecord.objects.filter(sheet__in=today_sheets).count()
        attendance_rate_today = round((student_present_today / total_records_today * 100), 1) if total_records_today > 0 else 0.0

        # 6. Fees & Finance Metrics
        today_fee_collection = StudentFeePayment.objects.filter(payment_date=today, is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        monthly_fee_collection = StudentFeePayment.objects.filter(
            payment_date__month=today.month,
            payment_date__year=today.year,
            is_deleted=False
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_income = StudentFeePayment.objects.filter(is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_expenses = Expense.objects.filter(is_deleted=False).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        outstanding_fees = StudentFeeInvoice.objects.filter(is_deleted=False).aggregate(Sum('balance_amount'))['balance_amount__sum'] or Decimal('0.00')

        # 7. Examination Card Metrics
        upcoming_exams = ExamSchedule.objects.filter(exam_date__gte=today, is_deleted=False).count()
        completed_exams = ExamSchedule.objects.filter(exam_date__lt=today, is_deleted=False).count()
        pending_results = ExamTerm.objects.filter(is_published=False, is_deleted=False).count()

        # 8. Library Card Metrics
        total_books = Book.objects.filter(is_deleted=False).aggregate(Sum('total_copies'))['total_copies__sum'] or Book.objects.filter(is_deleted=False).count()
        issued_books = BookCirculation.objects.filter(status=BookCirculation.Status.BORROWED, is_deleted=False).count()
        overdue_books = BookCirculation.objects.filter(status=BookCirculation.Status.BORROWED, due_date__lt=today, is_deleted=False).count()

        # Operational Attention & Low Inventory
        low_stock_items = [i for i in InventoryItem.objects.filter(is_deleted=False) if i.is_low_stock]
        pending_leaves = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING, is_deleted=False).count()
        pending_admissions = AdmissionsApplication.objects.filter(status__in=[AdmissionsApplication.Stage.SUBMITTED, AdmissionsApplication.Stage.UNDER_REVIEW], is_deleted=False).count()
        low_attendance_students_count = 0

        # AI & Operational Insights Engine
        ai_insights = []
        if len(low_stock_items) > 0:
            ai_insights.append({
                'type': 'warning',
                'icon': 'fa-triangle-exclamation',
                'title': 'Inventory Stock Alert',
                'message': f"{len(low_stock_items)} inventory asset(s) have fallen below their minimum reorder thresholds."
            })
        if outstanding_fees > Decimal('5000.00'):
            ai_insights.append({
                'type': 'danger',
                'icon': 'fa-circle-exclamation',
                'title': 'Fee Collection Arrears',
                'message': f"Outstanding student fee balance is ${outstanding_fees:,.2f}. Consider automated reminder broadcast."
            })
        if pending_leaves > 0:
            ai_insights.append({
                'type': 'info',
                'icon': 'fa-clock',
                'title': 'Faculty Leave Approvals Pending',
                'message': f"{pending_leaves} staff leave request(s) awaiting administrative review."
            })
        if pending_admissions > 0:
            ai_insights.append({
                'type': 'primary',
                'icon': 'fa-user-plus',
                'title': 'Admissions Pipeline Active',
                'message': f"{pending_admissions} prospective applicant(s) waiting for entrance review."
            })
        if not ai_insights and total_students == 0:
            ai_insights.append({
                'type': 'info',
                'icon': 'fa-circle-check',
                'title': 'Clean Database Ready',
                'message': 'Your system is clean and initialized. You can now add departments, enroll teachers, and register students.'
            })

        # Chart 1: Attendance Multi-Timeframe Datasets (Dynamic from DB)
        attendance_dates_7d = [(today - timezone.timedelta(days=i)).strftime('%d %b') for i in range(6, -1, -1)]
        attendance_values_7d = []
        for i in range(6, -1, -1):
            d = today - timezone.timedelta(days=i)
            sheets_d = StudentAttendanceSheet.objects.filter(date=d, is_deleted=False)
            if sheets_d.exists():
                p = StudentAttendanceRecord.objects.filter(sheet__in=sheets_d, status=StudentAttendanceRecord.Status.PRESENT).count()
                t = StudentAttendanceRecord.objects.filter(sheet__in=sheets_d).count()
                attendance_values_7d.append(round((p / t * 100), 1) if t > 0 else 0.0)
            else:
                attendance_values_7d.append(0.0)

        attendance_dates_30d = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        attendance_values_30d = [0.0, 0.0, 0.0, float(attendance_rate_today)]
        attendance_dates_ytd = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        attendance_values_ytd = [0.0] * len(attendance_dates_ytd)
        if attendance_rate_today > 0:
            attendance_values_ytd[today.month - 1] = float(attendance_rate_today)

        # Chart 2: Enrollment by Academic Year
        enrollment_years = ['2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
        enrollment_counts = [0, 0, 0, 0, total_students]

        # Chart 3: Academic Performance by Class
        classes_qs = ClassLevel.objects.filter(is_deleted=False).order_by('numeric_level')[:7]
        class_labels = [c.name for c in classes_qs]
        class_scores = []
        class_dist_pass = []
        for c in classes_qs:
            entries = ExamMarkEntry.objects.filter(student_enrollment__section__class_level=c, is_deleted=False)
            if entries.exists():
                avg_m = entries.aggregate(Avg('marks_obtained'))['marks_obtained__avg'] or 0.0
                class_scores.append(round(float(avg_m), 1))
                pass_cnt = entries.filter(is_passed=True).count()
                class_dist_pass.append(round((pass_cnt / entries.count() * 100), 1))
            else:
                class_scores.append(0.0)
                class_dist_pass.append(0)

        # Chart 4: Multi-Timeframe Finance Streams
        finance_7d_labels = [(today - timezone.timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
        finance_7d_income = []
        finance_7d_expenses = []
        for i in range(6, -1, -1):
            d = today - timezone.timedelta(days=i)
            inc = StudentFeePayment.objects.filter(payment_date=d, is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
            exp = Expense.objects.filter(expense_date=d, is_deleted=False).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            finance_7d_income.append(float(inc))
            finance_7d_expenses.append(float(exp))

        finance_30d_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        finance_30d_income = [0.0, 0.0, 0.0, float(monthly_fee_collection)]
        finance_30d_expenses = [0.0, 0.0, 0.0, float(total_expenses)]

        finance_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        finance_collections = [0.0] * len(finance_months)
        finance_expenses_list = [0.0] * len(finance_months)
        for m_idx in range(1, 13):
            m_inc = StudentFeePayment.objects.filter(payment_date__year=today.year, payment_date__month=m_idx, is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
            m_exp = Expense.objects.filter(expense_date__year=today.year, expense_date__month=m_idx, is_deleted=False).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            finance_collections[m_idx - 1] = float(m_inc)
            finance_expenses_list[m_idx - 1] = float(m_exp)

        # Admissions Conversion Funnel
        funnel_labels = ['Inquiries', 'Applications', 'Screening', 'Admitted']
        admissions_qs = AdmissionsApplication.objects.filter(is_deleted=False)
        funnel_counts = [
            admissions_qs.count(),
            admissions_qs.filter(status__in=[AdmissionsApplication.Stage.SUBMITTED, AdmissionsApplication.Stage.UNDER_REVIEW, AdmissionsApplication.Stage.SHORTLISTED, AdmissionsApplication.Stage.ACCEPTED, AdmissionsApplication.Stage.ENROLLED]).count(),
            admissions_qs.filter(status__in=[AdmissionsApplication.Stage.UNDER_REVIEW, AdmissionsApplication.Stage.SHORTLISTED, AdmissionsApplication.Stage.ACCEPTED, AdmissionsApplication.Stage.ENROLLED]).count(),
            new_admissions
        ]

        # Recent Students
        recent_students = Student.objects.filter(is_deleted=False).order_by('-admission_date', '-created_at')[:8]

        # Recent Activities / Audit Trail
        recent_audits = AuditLog.objects.all().order_by('-timestamp')[:8]

        # Today's Notices & Events
        recent_notices = Notice.objects.filter(is_published=True, is_deleted=False).order_by('-published_at', '-created_at')[:5]

        # Capacity & Financial Targets
        campus_capacity = 500
        capacity_pct = round((total_students / campus_capacity) * 100, 1) if (campus_capacity > 0 and total_students > 0) else 0.0
        annual_fee_target = Decimal('150000.00')
        fee_target_pct = min(100.0, round((float(total_income) / float(annual_fee_target)) * 100, 1)) if annual_fee_target > 0 else 0.0
        total_invoiced_fees = StudentFeeInvoice.objects.filter(is_deleted=False).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        from staff.models import StaffSalarySlip
        total_payroll_disbursed = StaffSalarySlip.objects.filter(payment_status=StaffSalarySlip.PaymentStatus.PAID, is_deleted=False).aggregate(Sum('net_salary'))['net_salary__sum'] or Decimal('0.00')
        fee_recovery_rate = round((float(total_income) / float(total_invoiced_fees) * 100), 1) if total_invoiced_fees > 0 else 0.0

        # Upcoming Academic & Campus Events
        upcoming_events_list = ExamSchedule.objects.filter(exam_date__gte=today, is_deleted=False).select_related('subject', 'class_level').order_by('exam_date')[:4]

        # Top 5 Overdue Fee Invoices
        top_fee_defaulters = StudentFeeInvoice.objects.filter(balance_amount__gt=0, is_deleted=False).select_related('student_enrollment__student').order_by('-balance_amount')[:5]

        # Recent 5 Online Admissions Applications
        recent_online_applications = AdmissionsApplication.objects.filter(is_deleted=False).select_related('applying_for_class').order_by('-applied_date', '-created_at')[:5]

        # Class-wise Fee Recovery Progress
        class_recovery_list = []
        for cl in classes_qs[:6]:
            invoiced_cl = StudentFeeInvoice.objects.filter(student_enrollment__section__class_level=cl, is_deleted=False).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            paid_cl = StudentFeePayment.objects.filter(invoice__student_enrollment__section__class_level=cl, is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
            pct = round((float(paid_cl) / float(invoiced_cl) * 100), 1) if invoiced_cl > 0 else 0.0
            class_recovery_list.append({
                'name': cl.name,
                'collected_pct': pct,
                'status_color': 'success' if pct >= 75 else 'primary'
            })

        # Donut Attendance Values (Clean 0s if no attendance taken today)
        donut_present = student_present_today
        donut_absent = student_absent_today
        donut_late = student_late_today
        donut_leave = 0

        # Multi-timeframe structures for interactive chart switcher
        chart_datasets = {
            'finance': {
                '7d': {'labels': finance_7d_labels, 'income': finance_7d_income, 'expenses': finance_7d_expenses},
                '30d': {'labels': finance_30d_labels, 'income': finance_30d_income, 'expenses': finance_30d_expenses},
                'ytd': {'labels': finance_months, 'income': finance_collections, 'expenses': finance_expenses_list}
            },
            'attendance': {
                '7d': {'labels': attendance_dates_7d, 'values': attendance_values_7d},
                '30d': {'labels': attendance_dates_30d, 'values': attendance_values_30d},
                'ytd': {'labels': attendance_dates_ytd, 'values': attendance_values_ytd}
            }
        }

        context.update({
            'page_title': 'Executive Command Center',
            'academic_year': academic_year,
            'recent_online_applications': recent_online_applications,
            'top_fee_defaulters': top_fee_defaulters,
            'class_recovery_list': class_recovery_list,
            'fee_recovery_rate': fee_recovery_rate,
            
            # 8 KPI Cards
            'total_students': total_students,
            'male_students': male_students,
            'female_students': female_students,
            'new_admissions': new_admissions,
            
            'total_teachers': total_teachers,
            'active_teachers': active_teachers,
            'teachers_on_leave': teachers_on_leave,
            
            'total_staff': total_staff,
            'staff_present_today': staff_present_today,
            'staff_absent_today': staff_absent_today,
            'staff_attendance_pct': staff_attendance_pct,

            'total_classes': total_classes,
            'total_sections': total_sections,

            'attendance_rate_today': attendance_rate_today,
            'student_present_today': student_present_today,
            'student_absent_today': student_absent_today,
            'student_late_today': student_late_today,

            'today_fee_collection': today_fee_collection,
            'monthly_fee_collection': monthly_fee_collection,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'outstanding_fees': outstanding_fees,
            'total_invoiced_fees': total_invoiced_fees,
            'total_payroll_disbursed': total_payroll_disbursed,

            # Gauges & Targets
            'campus_capacity': campus_capacity,
            'capacity_pct': capacity_pct,
            'annual_fee_target': annual_fee_target,
            'fee_target_pct': fee_target_pct,

            'upcoming_exams': upcoming_exams,
            'completed_exams': completed_exams,
            'pending_results': pending_results,

            'total_books': total_books,
            'issued_books': issued_books,
            'overdue_books': overdue_books,

            'low_stock_count': len(low_stock_items),
            'pending_leaves': pending_leaves,
            'pending_admissions': pending_admissions,
            'low_attendance_count': low_attendance_students_count,

            'ai_insights': ai_insights,
            'recent_students': recent_students,
            'recent_audits': recent_audits,
            'recent_notices': recent_notices,
            'upcoming_events_list': upcoming_events_list,

            # Donut Attendance Values
            'donut_present': donut_present,
            'donut_absent': donut_absent,
            'donut_late': donut_late,
            'donut_leave': donut_leave,

            # Charts JSON
            'chart_datasets_json': json.dumps(chart_datasets),
            'chart_attendance_labels': json.dumps(attendance_dates_7d),
            'chart_attendance_values': json.dumps(attendance_values_7d),
            'chart_enrollment_labels': json.dumps(enrollment_years),
            'chart_enrollment_values': json.dumps(enrollment_counts),
            'chart_performance_labels': json.dumps(class_labels),
            'chart_performance_values': json.dumps(class_scores),
            'chart_performance_pass': json.dumps(class_dist_pass),
            'chart_funnel_labels': json.dumps(funnel_labels),
            'chart_funnel_values': json.dumps(funnel_counts),
            'chart_finance_months': json.dumps(finance_months),
            'chart_finance_income': json.dumps(finance_collections),
            'chart_finance_expenses': json.dumps(finance_expenses_list),
            'chart_donut_data': json.dumps([donut_present, donut_absent, donut_late, donut_leave]),
        })
        return context


class PrincipalDashboardView(PrincipalRequiredMixin, AdminDashboardView):
    template_name = 'dashboards/principal_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Executive Principal Overview'
        return context


class TeacherDashboardView(TeacherRequiredMixin, TemplateView):
    template_name = 'dashboards/teacher_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        staff = getattr(user, 'staff_profile', None)

        iso_day = timezone.now().isoweekday()
        # Fallback to MONDAY (1) if weekend
        if iso_day in [6, 7]:
            iso_day = 1
        today_name = ClassTimetable.DayOfWeek(iso_day).label

        today_classes = []
        if staff:
            today_classes = ClassTimetable.objects.filter(
                teacher=staff, day_of_week=iso_day, is_deleted=False
            ).select_related('time_slot', 'section__class_level', 'subject').order_by('time_slot__start_time')

        # Recent Submissions Needing Evaluation
        pending_submissions = []
        if staff:
            pending_submissions = AssignmentSubmission.objects.filter(
                assignment__teacher=staff, graded_at__isnull=True, is_deleted=False
            ).select_related('student', 'assignment')[:8]

        # Active Homework
        active_assignments = []
        if staff:
            active_assignments = Assignment.objects.filter(teacher=staff, is_deleted=False).order_by('-due_date')[:5]

        context.update({
            'page_title': 'Teacher Academic Workspace',
            'staff': staff,
            'today_name': today_name,
            'today_classes': today_classes,
            'pending_submissions': pending_submissions,
            'active_assignments': active_assignments,
            'teacher_notices': Notice.objects.filter(
                is_published=True,
                target_audience__in=[Notice.Audience.ALL, Notice.Audience.TEACHERS],
                is_deleted=False
            )[:5],
        })
        return context


class AccountantDashboardView(AccountantRequiredMixin, TemplateView):
    template_name = 'dashboards/accountant_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_billed = StudentFeeInvoice.objects.filter(is_deleted=False).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        total_collected = StudentFeePayment.objects.filter(is_deleted=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
        total_outstanding = StudentFeeInvoice.objects.filter(is_deleted=False).aggregate(Sum('balance_amount'))['balance_amount__sum'] or Decimal('0.00')
        total_expenses = Expense.objects.filter(is_deleted=False).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        unpaid_invoices = StudentFeeInvoice.objects.filter(
            status__in=[StudentFeeInvoice.Status.UNPAID, StudentFeeInvoice.Status.PARTIAL], is_deleted=False
        ).select_related('student_enrollment__student', 'student_enrollment__section')[:10]

        recent_payments = StudentFeePayment.objects.filter(is_deleted=False).select_related('invoice__student_enrollment__student')[:8]

        context.update({
            'page_title': 'Financial Accounts & Billing Hub',
            'total_billed': total_billed,
            'total_collected': total_collected,
            'total_outstanding': total_outstanding,
            'total_expenses': total_expenses,
            'unpaid_invoices': unpaid_invoices,
            'recent_payments': recent_payments,
            'chart_finance': json.dumps([float(total_collected), float(total_expenses)]),
        })
        return context


class LibrarianDashboardView(LibrarianRequiredMixin, TemplateView):
    template_name = 'dashboards/librarian_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.filter(is_deleted=False)
        total_titles = books.count()
        total_copies = books.aggregate(Sum('total_copies'))['total_copies__sum'] or 0
        available_copies = books.aggregate(Sum('available_copies'))['available_copies__sum'] or 0
        borrowed_copies = max(0, total_copies - available_copies)

        active_loans = BookCirculation.objects.filter(status=BookCirculation.Status.BORROWED, is_deleted=False)
        overdue_loans = active_loans.filter(due_date__lt=timezone.now().date()).select_related('book', 'user')

        context.update({
            'page_title': 'Library Circulation Hub',
            'total_titles': total_titles,
            'total_copies': total_copies,
            'available_copies': available_copies,
            'borrowed_copies': borrowed_copies,
            'active_loans_count': active_loans.count(),
            'overdue_loans': overdue_loans[:10],
            'recent_loans': BookCirculation.objects.filter(is_deleted=False).select_related('book', 'user')[:8],
            'chart_copies': json.dumps([available_copies, borrowed_copies]),
        })
        return context


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    template_name = 'dashboards/student_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        student = getattr(user, 'student_profile', None)

        enrollment = None
        today_classes = []
        pending_assignments = []
        recent_grades = []
        unpaid_invoices = []
        attendance_pct = 95.0

        if student:
            enrollment = StudentEnrollment.objects.filter(student=student, is_current=True).select_related('section__class_level', 'academic_year').first()
            if enrollment:
                iso_day = timezone.now().isoweekday()
                if iso_day in [6, 7]:
                    iso_day = 1
                today_name = ClassTimetable.DayOfWeek(iso_day).label

                today_classes = ClassTimetable.objects.filter(
                    section=enrollment.section, day_of_week=iso_day, is_deleted=False
                ).select_related('time_slot', 'subject', 'teacher__user').order_by('time_slot__start_time')

                pending_assignments = Assignment.objects.filter(
                    section=enrollment.section, is_deleted=False
                ).exclude(submissions__student=student)[:5]

                unpaid_invoices = StudentFeeInvoice.objects.filter(
                    student_enrollment=enrollment, status__in=[StudentFeeInvoice.Status.UNPAID, StudentFeeInvoice.Status.PARTIAL]
                )

            recent_grades = ExamMarkEntry.objects.filter(
                student_enrollment__student=student, is_deleted=False
            ).select_related('exam_schedule__subject', 'exam_schedule__exam_term', 'grade')[:5]

        context.update({
            'page_title': 'Student Academic Portal',
            'student': student,
            'enrollment': enrollment,
            'today_classes': today_classes,
            'pending_assignments': pending_assignments,
            'recent_grades': recent_grades,
            'unpaid_invoices': unpaid_invoices,
            'attendance_pct': attendance_pct,
            'student_notices': Notice.objects.filter(
                is_published=True, target_audience__in=[Notice.Audience.ALL, Notice.Audience.STUDENTS], is_deleted=False
            )[:5],
        })
        return context


class ParentDashboardView(ParentRequiredMixin, TemplateView):
    template_name = 'dashboards/parent_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        parent = getattr(user, 'parent_profile', None)

        children = parent.children if parent else []
        active_child = None
        if children:
            child_id = self.request.session.get('active_child_id')
            if child_id:
                active_child = next((c for c in children if str(c.id) == str(child_id)), children[0])
            else:
                active_child = children[0]

        child_enrollment = None
        child_invoices = []
        child_grades = []
        if active_child:
            child_enrollment = StudentEnrollment.objects.filter(student=active_child, is_current=True).select_related('section__class_level').first()
            if child_enrollment:
                child_invoices = StudentFeeInvoice.objects.filter(
                    student_enrollment=child_enrollment, status__in=[StudentFeeInvoice.Status.UNPAID, StudentFeeInvoice.Status.PARTIAL]
                )
            child_grades = ExamMarkEntry.objects.filter(
                student_enrollment__student=active_child, is_deleted=False
            ).select_related('exam_schedule__subject', 'exam_schedule__exam_term', 'grade')[:5]

        context.update({
            'page_title': 'Parent & Guardian Portal',
            'parent': parent,
            'children': children,
            'active_child': active_child,
            'child_enrollment': child_enrollment,
            'child_invoices': child_invoices,
            'child_grades': child_grades,
            'parent_notices': Notice.objects.filter(
                is_published=True, target_audience__in=[Notice.Audience.ALL, Notice.Audience.PARENTS], is_deleted=False
            )[:5],
        })
        return context


class StaffDashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'dashboards/staff_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        my_leaves = LeaveRequest.objects.filter(user=user, is_deleted=False)[:5]
        assigned_assets = AssetAllocation.objects.filter(allocated_to_user=user, status=AssetAllocation.Status.ACTIVE)

        context.update({
            'page_title': 'Staff Self-Service Portal',
            'my_leaves': my_leaves,
            'assigned_assets': assigned_assets,
            'staff_notices': Notice.objects.filter(
                is_published=True, target_audience__in=[Notice.Audience.ALL, Notice.Audience.STAFF], is_deleted=False
            )[:5],
        })
        return context

