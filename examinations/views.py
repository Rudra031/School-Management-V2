import csv
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.db import transaction, models
from django.db.models import Sum, Avg, Count, Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

from examinations.models import GradeScale, ExamTerm, ExamSchedule, ExamMarkEntry
from examinations.forms import GradeScaleForm, ExamTermForm, ExamScheduleForm
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from fees.models import StudentFeeInvoice
from core.permissions import TeacherRequiredMixin, AdminOrPrincipalRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog, SchoolSetting

class ExamTermListView(AdminOrPrincipalRequiredMixin, ListView):
    model = ExamTerm
    template_name = 'examinations/exam_term_list.html'
    context_object_name = 'terms'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ExamTermForm()
        return context


class ExamTermCreateView(AdminOrPrincipalRequiredMixin, CreateView):
    model = ExamTerm
    form_class = ExamTermForm
    template_name = 'examinations/exam_term_form.html'
    success_url = reverse_lazy('examinations:term_list')

    def form_valid(self, form):
        messages.success(self.request, f"Exam Term '{form.cleaned_data['title']}' created successfully.")
        return super().form_valid(form)


class ExamScheduleListView(AdminOrPrincipalRequiredMixin, ListView):
    model = ExamSchedule
    template_name = 'examinations/schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        term_id = self.request.GET.get('term')
        class_id = self.request.GET.get('class_level')
        qs = ExamSchedule.objects.filter(is_deleted=False).select_related('exam_term', 'class_level', 'subject')
        if term_id:
            qs = qs.filter(exam_term_id=term_id)
        if class_id:
            qs = qs.filter(class_level_id=class_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['terms'] = ExamTerm.objects.filter(is_deleted=False)
        context['classes'] = ClassLevel.objects.filter(is_deleted=False)
        context['selected_term'] = self.request.GET.get('term', '')
        context['selected_class'] = self.request.GET.get('class_level', '')
        return context


class ExamScheduleCreateView(AdminOrPrincipalRequiredMixin, CreateView):
    model = ExamSchedule
    form_class = ExamScheduleForm
    template_name = 'examinations/schedule_form.html'
    success_url = reverse_lazy('examinations:schedule_list')

    def form_valid(self, form):
        messages.success(self.request, "Exam schedule item published.")
        return super().form_valid(form)


class ExamMarksEntryGridView(TeacherRequiredMixin, TemplateView):
    """
    Teacher Gradebook Grid for multi-component marks entry (Theory, Practical, Internal, Grace, Absent, Medical).
    """
    template_name = 'examinations/marks_entry_grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedule_id = self.request.GET.get('schedule')
        section_id = self.request.GET.get('section')

        schedules = ExamSchedule.objects.filter(is_deleted=False).select_related('exam_term', 'class_level', 'subject')
        selected_schedule = ExamSchedule.objects.filter(pk=schedule_id).first() if schedule_id else None

        sections = []
        selected_section = None
        student_rows = []

        if selected_schedule:
            sections = selected_schedule.class_level.sections.filter(is_deleted=False)
            selected_section = sections.filter(pk=section_id).first() if section_id else sections.first()

            if selected_section:
                enrollments = StudentEnrollment.objects.filter(
                    academic_year=selected_schedule.exam_term.academic_year,
                    section=selected_section,
                    is_current=True,
                    is_deleted=False
                ).select_related('student').order_by('roll_number')

                existing_marks = {m.student_enrollment_id: m for m in selected_schedule.marks.all()}

                for enroll in enrollments:
                    entry = existing_marks.get(enroll.id)
                    student_rows.append({
                        'enrollment': enroll,
                        'theory': entry.theory_marks_obtained if entry else Decimal('0.00'),
                        'practical': entry.practical_marks_obtained if entry else Decimal('0.00'),
                        'internal': entry.internal_marks_obtained if entry else Decimal('0.00'),
                        'grace': entry.grace_marks if entry else Decimal('0.00'),
                        'total': entry.total_marks_obtained if entry else Decimal('0.00'),
                        'grade': entry.grade.grade_letter if entry and entry.grade else '-',
                        'is_absent': entry.is_absent if entry else False,
                        'is_medical_leave': entry.is_medical_leave if entry else False,
                        'remarks': entry.remarks if entry else '',
                    })

        context['schedules'] = schedules
        context['selected_schedule'] = selected_schedule
        context['sections'] = sections
        context['selected_section'] = selected_section
        context['student_rows'] = student_rows
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        schedule_id = request.POST.get('schedule_id')
        section_id = request.POST.get('section_id')

        schedule = get_object_or_404(ExamSchedule, pk=schedule_id)
        section = get_object_or_404(Section, pk=section_id)

        enrollments = StudentEnrollment.objects.filter(
            academic_year=schedule.exam_term.academic_year,
            section=section,
            is_current=True,
            is_deleted=False
        )

        for enroll in enrollments:
            is_absent = request.POST.get(f'absent_{enroll.id}') == 'on'
            is_medical = request.POST.get(f'medical_{enroll.id}') == 'on'
            theory_str = request.POST.get(f'theory_{enroll.id}', '0').strip()
            practical_str = request.POST.get(f'practical_{enroll.id}', '0').strip()
            internal_str = request.POST.get(f'internal_{enroll.id}', '0').strip()
            grace_str = request.POST.get(f'grace_{enroll.id}', '0').strip()
            remarks = request.POST.get(f'remarks_{enroll.id}', '').strip()

            try:
                theory = Decimal(theory_str) if not is_absent and not is_medical and theory_str else Decimal('0.00')
                practical = Decimal(practical_str) if not is_absent and not is_medical and practical_str else Decimal('0.00')
                internal = Decimal(internal_str) if not is_absent and not is_medical and internal_str else Decimal('0.00')
                grace = Decimal(grace_str) if grace_str else Decimal('0.00')
            except Exception:
                theory, practical, internal, grace = Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

            # Cap marks
            if theory > schedule.theory_marks_max:
                theory = schedule.theory_marks_max
            if practical > schedule.practical_marks_max:
                practical = schedule.practical_marks_max
            if internal > schedule.internal_marks_max:
                internal = schedule.internal_marks_max

            entry, _ = ExamMarkEntry.objects.get_or_create(
                exam_schedule=schedule,
                student_enrollment=enroll,
                defaults={'entered_by': request.user}
            )
            entry.theory_marks_obtained = theory
            entry.practical_marks_obtained = practical
            entry.internal_marks_obtained = internal
            entry.grace_marks = grace
            entry.is_absent = is_absent
            entry.is_medical_leave = is_medical
            entry.remarks = remarks
            entry.entered_by = request.user
            entry.save()

        messages.success(request, f"Marks for {schedule.subject.name} ({section.full_name}) successfully saved.")
        log_audit(
            request,
            action=AuditLog.Action.UPDATE,
            module='Examinations',
            model_name='ExamMarkEntry',
            object_repr=f"Marks for {schedule} ({section})"
        )
        return redirect(f"{reverse('examinations:marks_entry')}?schedule={schedule.id}&section={section.id}")


class ExamAdmitCardView(RoleRequiredMixin, TemplateView):
    """
    Automated Hall Ticket / Admit Card Generator with Timetable, Photo, and Fee Clearance verification.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    template_name = 'examinations/admit_card_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = self.request.GET.get('student_id')
        section_id = self.request.GET.get('section_id')
        term_id = self.request.GET.get('term_id')

        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        term = ExamTerm.objects.filter(pk=term_id).first() if term_id else ExamTerm.objects.filter(academic_year=academic_year).first()

        cards = []
        enrollments = []

        if student_id:
            st = get_object_or_404(Student, pk=student_id)
            if st.current_enrollment:
                enrollments = [st.current_enrollment]
        elif section_id:
            enrollments = StudentEnrollment.objects.filter(
                section_id=section_id,
                academic_year=academic_year,
                is_current=True,
                is_deleted=False
            ).select_related('student', 'section__class_level').order_by('roll_number')
        elif self.request.user.is_student:
            student = getattr(self.request.user, 'student_profile', None)
            if student and student.current_enrollment:
                enrollments = [student.current_enrollment]
        elif self.request.user.is_parent:
            parent = getattr(self.request.user, 'parent_profile', None)
            if parent:
                children = parent.children
                enrollments = [c.current_enrollment for c in children if c.current_enrollment]

        for enroll in enrollments:
            schedules = []
            if term:
                schedules = ExamSchedule.objects.filter(
                    exam_term=term,
                    class_level=enroll.section.class_level,
                    is_deleted=False
                ).select_related('subject').order_by('exam_date', 'start_time')

            # Check Fee Clearance
            fee_due = Decimal('0.00')
            if term and term.requires_fee_clearance:
                invoices = StudentFeeInvoice.objects.filter(
                    student_enrollment=enroll,
                    is_deleted=False
                ).exclude(status=StudentFeeInvoice.Status.PAID)
                fee_due = invoices.aggregate(Sum('balance_amount'))['balance_amount__sum'] or Decimal('0.00')

            cards.append({
                'enrollment': enroll,
                'student': enroll.student,
                'schedules': schedules,
                'fee_due': fee_due,
                'fee_cleared': fee_due == Decimal('0.00')
            })

        context['term'] = term
        context['cards'] = cards
        context['school_setting'] = SchoolSetting.objects.first()
        return context


class ClassTabulationSheetView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    Master Class Results Tabulation Sheet with subject-wise marks, totals, percentages, ranks, and export.
    """
    template_name = 'examinations/tabulation_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        term_id = self.request.GET.get('term')
        section_id = self.request.GET.get('section')

        terms = ExamTerm.objects.filter(academic_year=academic_year, is_deleted=False) if academic_year else ExamTerm.objects.all()
        selected_term = ExamTerm.objects.filter(pk=term_id).first() if term_id else terms.first()
        sections = Section.objects.filter(is_deleted=False).select_related('class_level')
        selected_section = Section.objects.filter(pk=section_id).first() if section_id else sections.first()

        schedules = []
        student_rows = []
        class_average = Decimal('0.00')
        highest_pct = Decimal('0.00')
        passed_count = 0

        if selected_term and selected_section:
            schedules = ExamSchedule.objects.filter(
                exam_term=selected_term,
                class_level=selected_section.class_level,
                is_deleted=False
            ).select_related('subject').order_by('subject__name')

            enrollments = StudentEnrollment.objects.filter(
                academic_year=selected_term.academic_year,
                section=selected_section,
                is_current=True,
                is_deleted=False
            ).select_related('student').order_by('roll_number')

            total_term_max = sum([s.max_marks for s in schedules])

            for enroll in enrollments:
                subject_marks = {}
                student_total = Decimal('0.00')
                has_failed_subject = False

                for sch in schedules:
                    entry = ExamMarkEntry.objects.filter(exam_schedule=sch, student_enrollment=enroll).first()
                    obtained = entry.total_marks_obtained if entry else Decimal('0.00')
                    is_absent = entry.is_absent if entry else False
                    is_med = entry.is_medical_leave if entry else False
                    passed = entry.is_passed if entry else False
                    if not passed and not is_med:
                        has_failed_subject = True

                    student_total += obtained
                    subject_marks[sch.id] = {
                        'obtained': obtained,
                        'is_absent': is_absent,
                        'is_medical': is_med,
                        'passed': passed,
                        'grade': entry.grade.grade_letter if entry and entry.grade else '-'
                    }

                pct = round((student_total / total_term_max * 100), 2) if total_term_max > 0 else Decimal('0.00')
                overall_grade = GradeScale.get_grade_for_percentage(pct)
                is_overall_pass = pct >= selected_term.pass_percentage_threshold and not has_failed_subject

                if is_overall_pass:
                    passed_count += 1
                if pct > highest_pct:
                    highest_pct = pct

                student_rows.append({
                    'enrollment': enroll,
                    'student': enroll.student,
                    'subject_marks': subject_marks,
                    'total_obtained': student_total,
                    'percentage': pct,
                    'grade': overall_grade.grade_letter if overall_grade else '-',
                    'is_pass': is_overall_pass,
                })

            # Calculate Ranks
            student_rows.sort(key=lambda x: x['percentage'], reverse=True)
            for rank_idx, srow in enumerate(student_rows, 1):
                srow['rank'] = rank_idx

            # Restore Roll Number sort for table display
            student_rows.sort(key=lambda x: x['enrollment'].roll_number or 999)

            if student_rows:
                class_average = round(sum([s['percentage'] for s in student_rows]) / Decimal(len(student_rows)), 2)

        context['terms'] = terms
        context['selected_term'] = selected_term
        context['sections'] = sections
        context['selected_section'] = selected_section
        context['schedules'] = schedules
        context['student_rows'] = student_rows
        context['total_students'] = len(student_rows)
        context['passed_count'] = passed_count
        context['pass_rate'] = round((Decimal(passed_count) / Decimal(len(student_rows)) * 100), 1) if student_rows else 0
        context['highest_pct'] = highest_pct
        context['class_average'] = class_average
        return context


class StudentReportCardView(RoleRequiredMixin, DetailView):
    """
    Official Academic Transcript & Marksheet Report Card (CBSE/ICSE Compliant).
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    model = Student
    template_name = 'examinations/report_card.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        term_id = self.request.GET.get('term')

        terms_qs = ExamTerm.objects.filter(academic_year=academic_year) if academic_year else ExamTerm.objects.all()
        selected_term = ExamTerm.objects.filter(pk=term_id).first() if term_id else terms_qs.first()

        enrollment = self.object.current_enrollment
        marks_entries = []
        total_obtained = Decimal('0.00')
        total_max = Decimal('0.00')

        if enrollment and selected_term:
            marks_entries = ExamMarkEntry.objects.filter(
                student_enrollment=enrollment,
                exam_schedule__exam_term=selected_term
            ).select_related('exam_schedule__subject', 'grade')

            for entry in marks_entries:
                total_obtained += entry.total_marks_obtained
                total_max += entry.exam_schedule.max_marks

        overall_percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else Decimal('0.00')
        overall_grade = GradeScale.get_grade_for_percentage(overall_percentage)
        school_setting = SchoolSetting.objects.first()

        context['terms'] = terms_qs
        context['selected_term'] = selected_term
        context['enrollment'] = enrollment
        context['marks_entries'] = marks_entries
        context['total_obtained'] = total_obtained
        context['total_max'] = total_max
        context['overall_percentage'] = overall_percentage
        context['overall_grade'] = overall_grade
        context['school_setting'] = school_setting
        context['is_pass'] = overall_percentage >= (selected_term.pass_percentage_threshold if selected_term else 33.00)
        return context


class AcademicPromotionView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    Academic Progression & Annual Class Promotion Engine.
    """
    template_name = 'examinations/academic_promotion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        to_year = AcademicYear.objects.filter(start_date__gt=from_year.start_date).order_by('start_date').first() if from_year else None
        section_id = self.request.GET.get('section')

        sections = Section.objects.filter(is_deleted=False).select_related('class_level')
        selected_section = Section.objects.filter(pk=section_id).first() if section_id else sections.first()
        students_promotion_data = []

        if selected_section and from_year:
            enrollments = StudentEnrollment.objects.filter(
                academic_year=from_year,
                section=selected_section,
                is_current=True,
                is_deleted=False
            ).select_related('student')

            for enroll in enrollments:
                marks_qs = ExamMarkEntry.objects.filter(student_enrollment=enroll)
                total_marks = marks_qs.aggregate(Sum('total_marks_obtained'))['total_marks_obtained__sum'] or Decimal('0.00')
                total_max = marks_qs.aggregate(Sum('exam_schedule__max_marks'))['exam_schedule__max_marks__sum'] or Decimal('0.00')
                pct = round((total_marks / total_max * 100), 2) if total_max > 0 else Decimal('0.00')
                
                # Recommendation logic
                if pct >= 40:
                    status = 'PROMOTED'
                    badge_class = 'bg-success'
                elif pct >= 33:
                    status = 'CONDITIONAL'
                    badge_class = 'bg-warning text-dark'
                else:
                    status = 'DETAINED'
                    badge_class = 'bg-danger'

                students_promotion_data.append({
                    'enrollment': enroll,
                    'student': enroll.student,
                    'percentage': pct,
                    'recommendation': status,
                    'badge_class': badge_class
                })

        context['sections'] = sections
        context['selected_section'] = selected_section
        context['from_year'] = from_year
        context['to_year'] = to_year
        context['classes'] = ClassLevel.objects.filter(is_deleted=False)
        context['students_promotion_data'] = students_promotion_data
        return context


class StudentReportCardPDFDownloadView(RoleRequiredMixin, View):
    """
    Generates and streams official CBSE / State Board standard student report card PDF.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']

    def get(self, request, pk, *args, **kwargs):
        student = get_object_or_404(Student, pk=pk, is_deleted=False)
        term_id = request.GET.get('term')
        academic_year = getattr(request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        terms_qs = ExamTerm.objects.filter(academic_year=academic_year) if academic_year else ExamTerm.objects.all()
        selected_term = ExamTerm.objects.filter(pk=term_id).first() if term_id else terms_qs.first()

        from core.pdf_generator import generate_report_card_pdf
        from django.http import HttpResponse

        pdf_buffer = generate_report_card_pdf(student, selected_term)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        term_title_str = getattr(selected_term, 'title', getattr(selected_term, 'name', 'Annual')) if selected_term else 'Annual'
        term_name = term_title_str.replace(" ", "_")
        response['Content-Disposition'] = f'inline; filename="ReportCard_{student.admission_number}_{term_name}.pdf"'
        return response

