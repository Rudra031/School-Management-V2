import json
import calendar
from datetime import datetime, date
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, TemplateView
from django.db import transaction
from django.contrib import messages
from django.utils import timezone

from attendance.models import StudentAttendanceSheet, StudentAttendanceRecord, StaffAttendanceRecord
from attendance.forms import AttendanceFilterForm, StaffAttendanceForm
from academics.models import AcademicYear, Section
from students.models import StudentEnrollment
from staff.models import StaffMember
from core.permissions import TeacherRequiredMixin, AdminOrPrincipalRequiredMixin
from core.utils import log_audit
from core.models import AuditLog


STATUS_CONFIG = {
    'PRESENT': {'letter': 'P', 'label': 'Present', 'color': '#10b981', 'badge_class': 'bg-success', 'text_class': 'text-success'},
    'ABSENT': {'letter': 'A', 'label': 'Absent', 'color': '#ef4444', 'badge_class': 'bg-danger', 'text_class': 'text-danger'},
    'LATE': {'letter': 'L', 'label': 'Late', 'color': '#f59e0b', 'badge_class': 'bg-warning', 'text_class': 'text-warning'},
    'HALF_DAY': {'letter': 'HD', 'label': 'Half Day', 'color': '#8b5cf6', 'badge_class': 'bg-purple', 'text_class': 'text-purple'},
    'EXCUSED_LEAVE': {'letter': 'LV', 'label': 'Leave', 'color': '#0ea5e9', 'badge_class': 'bg-info', 'text_class': 'text-info'},
}


class DailyAttendanceMarkingView(TeacherRequiredMixin, TemplateView):
    """
    High-Speed Daily Section Attendance Marking Sheet.
    Features interactive single-click status cycling and live summary metrics.
    """
    template_name = 'attendance/mark_attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        section_id = self.request.GET.get('section')
        date_str = self.request.GET.get('date')

        selected_date = timezone.now().date()
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()

        sections_qs = Section.objects.filter(is_deleted=False).select_related('class_level')
        
        # If teacher, highlight assigned sections
        if self.request.user.is_teacher and not section_id:
            staff_member = getattr(self.request.user, 'staff_profile', None)
            if staff_member:
                assigned_sec = staff_member.assigned_class_sections.first()
                if assigned_sec:
                    section_id = str(assigned_sec.id)

        selected_section = Section.objects.filter(pk=section_id).first() if section_id else sections_qs.first()

        student_rows = []
        sheet = None
        counts = {'PRESENT': 0, 'ABSENT': 0, 'LATE': 0, 'HALF_DAY': 0, 'EXCUSED_LEAVE': 0}

        if selected_section and academic_year:
            sheet, _ = StudentAttendanceSheet.objects.get_or_create(
                academic_year=academic_year,
                section=selected_section,
                date=selected_date,
                defaults={'taken_by': self.request.user}
            )

            enrollments = StudentEnrollment.objects.filter(
                academic_year=academic_year,
                section=selected_section,
                is_current=True,
                is_deleted=False
            ).select_related('student').order_by('roll_number')

            existing_records = {r.student_enrollment_id: r for r in sheet.records.all()}

            for enroll in enrollments:
                record = existing_records.get(enroll.id)
                st = record.status if record else 'PRESENT'
                counts[st] = counts.get(st, 0) + 1
                
                conf = STATUS_CONFIG.get(st, STATUS_CONFIG['PRESENT'])
                student_rows.append({
                    'enrollment': enroll,
                    'status': st,
                    'status_conf': conf,
                    'remarks': record.remarks if record else '',
                })

        total_marked = len(student_rows)
        present_equivalent = counts['PRESENT'] + (counts['HALF_DAY'] * 0.5)
        att_pct = round((present_equivalent / total_marked * 100), 1) if total_marked > 0 else 100.0

        context.update({
            'academic_year': academic_year,
            'sections': sections_qs,
            'selected_section': selected_section,
            'selected_date': selected_date,
            'student_rows': student_rows,
            'sheet': sheet,
            'counts': counts,
            'total_marked': total_marked,
            'att_pct': att_pct,
            'status_config': STATUS_CONFIG,
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        academic_year = getattr(request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        section_id = request.POST.get('section_id')
        date_str = request.POST.get('date')

        section = get_object_or_404(Section, pk=section_id)
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        sheet, _ = StudentAttendanceSheet.objects.get_or_create(
            academic_year=academic_year,
            section=section,
            date=selected_date,
            defaults={'taken_by': request.user}
        )
        sheet.taken_by = request.user
        sheet.save()

        enrollments = StudentEnrollment.objects.filter(
            academic_year=academic_year,
            section=section,
            is_current=True,
            is_deleted=False
        )

        for enroll in enrollments:
            status_val = request.POST.get(f'status_{enroll.id}', 'PRESENT')
            remarks_val = request.POST.get(f'remarks_{enroll.id}', '')

            StudentAttendanceRecord.objects.update_or_create(
                sheet=sheet,
                student_enrollment=enroll,
                defaults={
                    'status': status_val,
                    'remarks': remarks_val
                }
            )

        messages.success(request, f"Attendance for {section.full_name} on {selected_date.strftime('%d %b %Y')} successfully saved.")
        log_audit(
            request,
            action=AuditLog.Action.CREATE,
            module='Attendance',
            model_name='StudentAttendanceSheet',
            object_id=str(sheet.id),
            object_repr=f"{section} - {selected_date}"
        )
        return redirect(f"{reverse('attendance:mark')}?section={section.id}&date={selected_date.strftime('%Y-%m-%d')}")


class MonthlyAttendanceMatrixView(TeacherRequiredMixin, TemplateView):
    """
    Modern Full-Month Attendance Grid & Interactive Click-To-Cycle Matrix.
    Displays all days of the month horizontally with live status badges.
    """
    template_name = 'attendance/monthly_matrix.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        section_id = self.request.GET.get('section')
        today = timezone.now().date()
        
        try:
            year = int(self.request.GET.get('year', today.year))
            month = int(self.request.GET.get('month', today.month))
        except (ValueError, TypeError):
            year, month = today.year, today.month

        sections_qs = Section.objects.filter(is_deleted=False).select_related('class_level')
        selected_section = Section.objects.filter(pk=section_id).first() if section_id else sections_qs.first()

        # Build list of days for month
        num_days = calendar.monthrange(year, month)[1]
        days_header = []
        for d in range(1, num_days + 1):
            cur_date = date(year, month, d)
            weekday_name = cur_date.strftime('%a')[:2] # Mo, Tu, We, Th, Fr, Sa, Su
            is_sunday = cur_date.weekday() == 6
            days_header.append({
                'day_num': d,
                'date_str': cur_date.strftime('%Y-%m-%d'),
                'weekday': weekday_name,
                'is_sunday': is_sunday,
                'is_today': cur_date == today,
            })

        matrix_rows = []
        month_present_total = 0
        month_absent_total = 0

        if selected_section and academic_year:
            # Prefetch all sheets for this section in the month
            start_date = date(year, month, 1)
            end_date = date(year, month, num_days)
            
            sheets = StudentAttendanceSheet.objects.filter(
                academic_year=academic_year,
                section=selected_section,
                date__gte=start_date,
                date__lte=end_date
            ).prefetch_related('records')

            # Build map: (enrollment_id, date) -> record
            record_map = {}
            for sh in sheets:
                for rec in sh.records.all():
                    record_map[(rec.student_enrollment_id, sh.date)] = rec

            enrollments = StudentEnrollment.objects.filter(
                academic_year=academic_year,
                section=selected_section,
                is_current=True,
                is_deleted=False
            ).select_related('student').order_by('roll_number')

            for enroll in enrollments:
                p_cnt = 0
                a_cnt = 0
                l_cnt = 0
                hd_cnt = 0
                lv_cnt = 0
                
                day_cells = []
                for d_info in days_header:
                    cur_date = date(year, month, d_info['day_num'])
                    rec = record_map.get((enroll.id, cur_date))
                    
                    if rec:
                        st = rec.status
                        if st == 'PRESENT': p_cnt += 1
                        elif st == 'ABSENT': a_cnt += 1
                        elif st == 'LATE': l_cnt += 1
                        elif st == 'HALF_DAY': hd_cnt += 1
                        elif st == 'EXCUSED_LEAVE': lv_cnt += 1
                    else:
                        st = 'NONE'

                    conf = STATUS_CONFIG.get(st, {
                        'letter': '·' if not d_info['is_sunday'] else '—',
                        'label': 'Not Marked',
                        'color': '#475569',
                        'badge_class': 'bg-secondary bg-opacity-25',
                        'text_class': 'text-muted'
                    })

                    day_cells.append({
                        'day_num': d_info['day_num'],
                        'date_str': d_info['date_str'],
                        'status': st,
                        'letter': conf['letter'],
                        'color': conf['color'],
                        'badge_class': conf['badge_class'],
                        'is_sunday': d_info['is_sunday'],
                    })

                total_active_days = p_cnt + a_cnt + l_cnt + hd_cnt + lv_cnt
                present_score = p_cnt + l_cnt + (hd_cnt * 0.5)
                pct = round((present_score / total_active_days * 100), 1) if total_active_days > 0 else 100.0

                month_present_total += p_cnt
                month_absent_total += a_cnt

                matrix_rows.append({
                    'enrollment': enroll,
                    'student': enroll.student,
                    'day_cells': day_cells,
                    'present_count': p_cnt,
                    'absent_count': a_cnt,
                    'late_count': l_cnt,
                    'half_day_count': hd_cnt,
                    'leave_count': lv_cnt,
                    'attendance_pct': pct,
                })

        months_list = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        years_list = range(today.year - 2, today.year + 3)

        context.update({
            'academic_year': academic_year,
            'sections': sections_qs,
            'selected_section': selected_section,
            'selected_year': year,
            'selected_month': month,
            'month_name': calendar.month_name[month],
            'months_list': months_list,
            'years_list': years_list,
            'days_header': days_header,
            'matrix_rows': matrix_rows,
            'total_students': len(matrix_rows),
            'status_config': STATUS_CONFIG,
        })
        return context


class AttendanceCellUpdateAPIView(TeacherRequiredMixin, View):
    """
    Rapid AJAX API to cycle or update individual student attendance cells in real time.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        enrollment_id = data.get('enrollment_id')
        date_str = data.get('date')
        new_status = data.get('status', 'PRESENT')

        if not enrollment_id or not date_str:
            return JsonResponse({'success': False, 'message': 'Missing enrollment ID or date.'}, status=400)

        enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_id)
        att_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        sheet, _ = StudentAttendanceSheet.objects.get_or_create(
            academic_year=enrollment.academic_year,
            section=enrollment.section,
            date=att_date,
            defaults={'taken_by': request.user}
        )

        record, _ = StudentAttendanceRecord.objects.update_or_create(
            sheet=sheet,
            student_enrollment=enrollment,
            defaults={'status': new_status}
        )

        conf = STATUS_CONFIG.get(new_status, STATUS_CONFIG['PRESENT'])

        return JsonResponse({
            'success': True,
            'enrollment_id': enrollment_id,
            'date': date_str,
            'status': new_status,
            'letter': conf['letter'],
            'color': conf['color'],
            'badge_class': conf['badge_class'],
            'label': conf['label'],
        })


class AttendanceReportView(TeacherRequiredMixin, TemplateView):
    """
    Monthly section attendance matrix and low attendance alert dashboard.
    """
    template_name = 'attendance/attendance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        section_id = self.request.GET.get('section')

        sections_qs = Section.objects.filter(is_deleted=False).select_related('class_level')
        selected_section = Section.objects.filter(pk=section_id).first() if section_id else sections_qs.first()

        report_rows = []
        threshold = 75.0

        if selected_section and academic_year:
            enrollments = StudentEnrollment.objects.filter(
                academic_year=academic_year,
                section=selected_section,
                is_current=True,
                is_deleted=False
            ).select_related('student').order_by('roll_number')

            total_sheets = StudentAttendanceSheet.objects.filter(academic_year=academic_year, section=selected_section).count()

            for enroll in enrollments:
                present_days = StudentAttendanceRecord.objects.filter(
                    student_enrollment=enroll,
                    status__in=[StudentAttendanceRecord.Status.PRESENT, StudentAttendanceRecord.Status.HALF_DAY]
                ).count()
                absent_days = StudentAttendanceRecord.objects.filter(
                    student_enrollment=enroll,
                    status=StudentAttendanceRecord.Status.ABSENT
                ).count()

                percentage = round((present_days / total_sheets * 100), 1) if total_sheets > 0 else 100.0
                is_low = percentage < threshold

                report_rows.append({
                    'student': enroll.student,
                    'roll_number': enroll.roll_number,
                    'total_days': total_sheets,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'percentage': percentage,
                    'is_low_attendance': is_low,
                })

        context['sections'] = sections_qs
        context['selected_section'] = selected_section
        context['report_rows'] = report_rows
        context['threshold'] = threshold
        return context


class StaffAttendanceListView(AdminOrPrincipalRequiredMixin, ListView):
    model = StaffAttendanceRecord
    template_name = 'attendance/staff_attendance.html'
    context_object_name = 'attendance_logs'
    paginate_by = 30

    def get_queryset(self):
        date_str = self.request.GET.get('date')
        selected_date = timezone.now().date()
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()
        return StaffAttendanceRecord.objects.filter(date=selected_date).select_related('staff_member__designation')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_date'] = self.request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
        context['form'] = StaffAttendanceForm()
        return context
