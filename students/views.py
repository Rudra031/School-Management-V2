from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, TemplateView
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

from students.models import Student, StudentEnrollment, StudentHealthRecord, StudentMedicalIncident
from students.forms import (
    StudentRegistrationForm, StudentUpdateForm, StudentHealthRecordForm,
    StudentMedicalIncidentForm, StudentPromotionForm
)
from academics.models import AcademicYear, ClassLevel, Section
from core.permissions import AdminOrPrincipalRequiredMixin, SchoolAdminRequiredMixin, RoleRequiredMixin
from core.utils import log_audit, export_to_csv, export_to_excel
from core.models import AuditLog

class StudentListView(AdminOrPrincipalRequiredMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        qs = Student.objects.filter(is_deleted=False).prefetch_related(
            'enrollments__section__class_level', 'enrollments__academic_year'
        )
        search_query = self.request.GET.get('search', '').strip()
        class_id = self.request.GET.get('class_level')
        section_id = self.request.GET.get('section')
        status = self.request.GET.get('status')
        gender = self.request.GET.get('gender')

        if search_query:
            qs = qs.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(admission_number__icontains=search_query) |
                Q(student_id__icontains=search_query)
            )
        if class_id:
            qs = qs.filter(enrollments__section__class_level_id=class_id, enrollments__is_current=True)
        if section_id:
            qs = qs.filter(enrollments__section_id=section_id, enrollments__is_current=True)
        if status:
            qs = qs.filter(status=status)
        if gender:
            qs = qs.filter(gender=gender)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = ClassLevel.objects.filter(is_deleted=False).prefetch_related('sections')
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_class'] = self.request.GET.get('class_level', '')
        context['selected_section'] = self.request.GET.get('section', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_gender'] = self.request.GET.get('gender', '')
        context['view_mode'] = self.request.GET.get('view', 'grid')
        context['total_active_count'] = Student.objects.filter(status=Student.Status.ACTIVE, is_deleted=False).count()
        context['total_graduated_count'] = Student.objects.filter(status=Student.Status.GRADUATED, is_deleted=False).count()
        return context


from decimal import Decimal
from django.db.models import Sum, Avg, Count

from attendance.models import StudentAttendanceRecord
from timetable.models import ClassTimetable
from assignments.models import Assignment, AssignmentSubmission
from examinations.models import ExamMarkEntry
from fees.models import StudentFeeInvoice, StudentFeePayment
from library.models import BookCirculation
from documents.models import SchoolDocument
from admissions.models import AdmissionsApplication


class StudentDetailView(AdminOrPrincipalRequiredMixin, DetailView):
    """
    Central Student Profile (Unified 360° View).
    Aggregates all interconnected academic, attendance, exam, fee, homework,
    library, document, health, and audit records into a single unified dashboard.
    """
    model = Student
    template_name = 'students/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        
        # 1. Enrollments & Current Placement
        enrollments = student.enrollments.filter(is_deleted=False).select_related(
            'section__class_level', 'academic_year'
        ).order_by('-academic_year__start_date', '-is_current')
        current_enrollment = student.current_enrollment
        context['enrollments'] = enrollments
        context['current_enrollment'] = current_enrollment

        # 2. Parents / Guardians
        context['parents'] = student.parent_relations.filter(is_deleted=False).select_related('parent__user')

        # 3. Admission Application
        context['admission_app'] = AdmissionsApplication.objects.filter(
            Q(first_name__iexact=student.first_name, last_name__iexact=student.last_name) |
            Q(parent_phone=student.emergency_contact_phone)
        ).first()

        # 4. Attendance Stats & Logs
        attendance_records = StudentAttendanceRecord.objects.filter(
            student_enrollment__student=student, is_deleted=False
        ).select_related('sheet__section', 'sheet__academic_year').order_by('-sheet__date')
        
        total_att = attendance_records.count()
        present_att = attendance_records.filter(status=StudentAttendanceRecord.Status.PRESENT).count()
        absent_att = attendance_records.filter(status=StudentAttendanceRecord.Status.ABSENT).count()
        late_att = attendance_records.filter(status=StudentAttendanceRecord.Status.LATE).count()
        att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0.0
        
        context['attendance_records'] = attendance_records[:40]
        context['attendance_total'] = total_att
        context['attendance_present'] = present_att
        context['attendance_absent'] = absent_att
        context['attendance_late'] = late_att
        context['attendance_pct'] = att_pct

        # 5. Class Timetable
        if current_enrollment:
            context['timetable_entries'] = ClassTimetable.objects.filter(
                section=current_enrollment.section, is_deleted=False
            ).select_related('time_slot', 'subject', 'teacher__user').order_by('day_of_week', 'time_slot__period_number')
        else:
            context['timetable_entries'] = []

        # 6. Homework & Assignments
        if current_enrollment:
            context['assignments'] = Assignment.objects.filter(
                section=current_enrollment.section, is_deleted=False
            ).select_related('subject', 'teacher__user').order_by('-due_date')[:15]
            context['submissions'] = AssignmentSubmission.objects.filter(
                student_enrollment=current_enrollment, is_deleted=False
            ).select_related('assignment__subject')
        else:
            context['assignments'] = []
            context['submissions'] = []

        # 7. Examination Marks & Grades
        exam_marks = ExamMarkEntry.objects.filter(
            student_enrollment__student=student, is_deleted=False
        ).select_related('exam_schedule__exam_term', 'exam_schedule__subject', 'grade').order_by('-exam_schedule__exam_date')
        context['exam_marks'] = exam_marks
        if exam_marks.exists():
            context['avg_marks_pct'] = round(sum(m.percentage for m in exam_marks) / exam_marks.count(), 1)
        else:
            context['avg_marks_pct'] = None

        # 8. Fees & Invoices
        fee_invoices = StudentFeeInvoice.objects.filter(
            student_enrollment__student=student, is_deleted=False
        ).select_related('academic_year').order_by('-issue_date')
        fee_payments = StudentFeePayment.objects.filter(
            invoice__student_enrollment__student=student, is_deleted=False
        ).select_related('invoice', 'collected_by').order_by('-payment_date')
        
        total_billed = sum(inv.net_payable for inv in fee_invoices)
        total_paid = sum(p.amount_paid for p in fee_payments)
        total_balance = sum(inv.balance_amount for inv in fee_invoices)
        
        context['fee_invoices'] = fee_invoices
        context['fee_payments'] = fee_payments
        context['total_fee_billed'] = total_billed
        context['total_fee_paid'] = total_paid
        context['total_fee_balance'] = total_balance

        # 9. Library Circulations
        if student.user:
            context['library_circulations'] = BookCirculation.objects.filter(
                user=student.user, is_deleted=False
            ).select_related('book', 'issued_by').order_by('-borrow_date')
        else:
            context['library_circulations'] = BookCirculation.objects.none()

        # 10. Health & Medical Record
        context['health_record'] = getattr(student, 'health_record', None)
        context['medical_incidents'] = student.medical_incidents.filter(is_deleted=False).select_related('reported_by').order_by('-incident_date')

        # 11. Documents
        context['documents'] = student.attached_documents.filter(is_deleted=False).select_related('category', 'uploaded_by')

        # 12. Audit Log
        context['audit_logs'] = AuditLog.objects.filter(
            object_id=str(student.id)
        ).select_related('user').order_by('-timestamp')[:15]

        return context


class StudentRegistrationView(SchoolAdminRequiredMixin, CreateView):
    model = Student
    form_class = StudentRegistrationForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('students:student_list')

    def form_valid(self, form):
        messages.success(self.request, f"Student '{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}' enrolled successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Students',
            model_name='Student',
            object_id=str(self.object.id),
            object_repr=self.object.full_name
        )
        return response


class StudentUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = Student
    form_class = StudentUpdateForm
    template_name = 'students/student_form.html'

    def get_success_url(self):
        return reverse_lazy('students:student_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Student '{self.object.full_name}' updated successfully.")
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Students',
            model_name='Student',
            object_id=str(self.object.id),
            object_repr=self.object.full_name,
            changes={'updated_fields': list(form.changed_data)}
        )
        return super().form_valid(form)


class StudentHealthView(RoleRequiredMixin, DetailView):
    """
    Restricted Health & Medical Record View.
    Accessible only to SuperAdmin, Principal, SchoolAdmin, or authorized medical personnel.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN']
    model = Student
    template_name = 'students/student_health.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        health_record, _ = StudentHealthRecord.objects.get_or_create(student=self.object)
        context['health_record'] = health_record
        context['health_form'] = StudentHealthRecordForm(instance=health_record)
        context['incidents'] = self.object.medical_incidents.filter(is_deleted=False)
        context['incident_form'] = StudentMedicalIncidentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        health_record, _ = StudentHealthRecord.objects.get_or_create(student=self.object)
        form = StudentHealthRecordForm(request.POST, instance=health_record)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical and health record updated.")
            log_audit(
                request,
                action=AuditLog.Action.UPDATE,
                module='StudentHealth',
                model_name='StudentHealthRecord',
                object_id=str(health_record.id),
                object_repr=f"Health Record: {self.object.full_name}"
            )
        return redirect('students:student_health', pk=self.object.pk)


class StudentMedicalIncidentCreateView(RoleRequiredMixin, View):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN']

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentMedicalIncidentForm(request.POST)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.student = student
            incident.reported_by = request.user
            incident.save()
            messages.success(request, "Medical incident logged successfully.")
        return redirect('students:student_health', pk=student.pk)


class StudentPromotionView(SchoolAdminRequiredMixin, FormView):
    """
    Wizard to promote all active students from one Class/Section to the next for a new Academic Year.
    """
    template_name = 'students/student_promotion.html'
    form_class = StudentPromotionForm
    success_url = reverse_lazy('students:student_list')

    def form_valid(self, form):
        from_year = form.cleaned_data['from_academic_year']
        from_section = form.cleaned_data['from_section']
        to_year = form.cleaned_data['to_academic_year']
        to_section = form.cleaned_data['to_section']

        # Find current active enrollments
        current_enrollments = StudentEnrollment.objects.filter(
            academic_year=from_year,
            section=from_section,
            is_current=True,
            is_deleted=False
        ).select_related('student')

        count = 0
        for enrollment in current_enrollments:
            # Mark previous as PROMOTED and not current
            enrollment.promotion_status = StudentEnrollment.PromotionStatus.PROMOTED
            enrollment.is_current = False
            enrollment.save(update_fields=['promotion_status', 'is_current'])

            # Create new enrollment in destination section
            StudentEnrollment.objects.create(
                student=enrollment.student,
                academic_year=to_year,
                section=to_section,
                roll_number=enrollment.roll_number,
                enrollment_date=timezone.now().date(),
                is_current=True,
                promotion_status=StudentEnrollment.PromotionStatus.ENROLLED
            )
            count += 1

        messages.success(self.request, f"Successfully promoted {count} students from {from_section} ({from_year.name}) to {to_section} ({to_year.name}).")
        log_audit(
            self.request,
            action=AuditLog.Action.BULK_ACTION,
            module='Students',
            model_name='StudentEnrollment',
            object_repr=f"Promoted {count} students to {to_section} ({to_year.name})"
        )
        return super().form_valid(form)


class StudentExportView(AdminOrPrincipalRequiredMixin, View):
    def get(self, request):
        export_type = request.GET.get('format', 'excel')
        students_qs = Student.objects.filter(is_deleted=False).prefetch_related('enrollments__section__class_level')

        headers = ['Admission No', 'Student ID', 'Full Name', 'Gender', 'Date of Birth', 'Class & Section', 'Status', 'Emergency Phone']
        rows = [
            [
                s.admission_number,
                s.student_id,
                s.full_name,
                s.get_gender_display(),
                s.date_of_birth.strftime('%Y-%m-%d'),
                s.current_class_section,
                s.get_status_display(),
                s.emergency_contact_phone
            ]
            for s in students_qs
        ]

        if export_type == 'csv':
            return export_to_csv('student_directory', headers, rows)
        return export_to_excel('student_directory', 'Students', headers, rows)


from core.permissions import StudentRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from timetable.models import ClassTimetable
from attendance.models import StudentAttendanceRecord
from fees.models import StudentFeeInvoice

class StudentMyTimetableView(StudentRequiredMixin, TemplateView):
    """
    Dedicated view for a student to inspect their weekly class timetable matrix.
    """
    template_name = 'students/my_timetable.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = getattr(self.request.user, 'student_profile', None)
        enrollment = student.current_enrollment if student else None
        timetable_by_day = {}
        days = ClassTimetable.DayOfWeek.choices

        if enrollment:
            slots = ClassTimetable.objects.filter(
                section=enrollment.section, is_deleted=False
            ).select_related('time_slot', 'subject', 'teacher__user').order_by('day_of_week', 'time_slot__start_time')

            for day_code, day_name in days:
                day_slots = [s for s in slots if s.day_of_week == day_code]
                if day_slots:
                    timetable_by_day[day_name] = day_slots

        context.update({
            'student': student,
            'enrollment': enrollment,
            'timetable_by_day': timetable_by_day,
            'page_title': 'My Weekly Class Schedule',
        })
        return context


class StudentMyAttendanceView(StudentRequiredMixin, TemplateView):
    """
    Dedicated full-page attendance ledger and rate calculator for the student.
    """
    template_name = 'students/my_attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = getattr(self.request.user, 'student_profile', None)
        enrollment = student.current_enrollment if student else None

        records = StudentAttendanceRecord.objects.filter(
            student_enrollment__student=student, is_deleted=False
        ).select_related('sheet__section', 'sheet__academic_year').order_by('-sheet__date') if student else []


        total_sessions = len(records)
        present_count = sum(1 for r in records if r.status == StudentAttendanceRecord.Status.PRESENT)
        absent_count = sum(1 for r in records if r.status == StudentAttendanceRecord.Status.ABSENT)
        late_count = sum(1 for r in records if r.status == StudentAttendanceRecord.Status.LATE)
        half_day_count = sum(1 for r in records if r.status == StudentAttendanceRecord.Status.HALF_DAY)

        rate = round(((present_count + late_count + 0.5 * half_day_count) / total_sessions * 100), 1) if total_sessions > 0 else 100.0

        context.update({
            'student': student,
            'enrollment': enrollment,
            'records': records[:60],
            'total_sessions': total_sessions,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'half_day_count': half_day_count,
            'attendance_rate': rate,
            'page_title': 'My Attendance History & Analytics',
        })
        return context


class StudentIDCardView(LoginRequiredMixin, DetailView):
    """
    Printable PVC / A4 Identity Card view for a student.
    Accessible by the student, their parents, and school administrators.
    """
    model = Student
    template_name = 'students/student_id_card.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        context['enrollment'] = student.current_enrollment
        from core.models import SchoolSetting
        context['school_setting'] = SchoolSetting.get_settings()
        return context

