from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, DeleteView, TemplateView
from django.contrib import messages

from timetable.models import TimeSlot, ClassTimetable
from timetable.forms import TimeSlotForm, ClassTimetableForm
from academics.models import AcademicYear, Section
from staff.models import StaffMember
from core.permissions import AdminOrPrincipalRequiredMixin, SchoolAdminRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class TimetableOverviewView(RoleRequiredMixin, TemplateView):
    """
    Weekly Timetable Matrix Grid View.
    Supports filtering by Section (for students/teachers/admins) or by Teacher.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    template_name = 'timetable/timetable_grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        
        section_id = self.request.GET.get('section')
        teacher_id = self.request.GET.get('teacher')

        # Auto-detect section for student or parent
        if self.request.user.is_student:
            enrollment = getattr(self.request.user, 'student_profile', None)
            if enrollment and enrollment.current_enrollment:
                section_id = str(enrollment.current_enrollment.section_id)
        elif self.request.user.is_teacher and not section_id and not teacher_id:
            staff_profile = getattr(self.request.user, 'staff_profile', None)
            if staff_profile:
                teacher_id = str(staff_profile.id)

        selected_section = Section.objects.filter(pk=section_id).first() if section_id else Section.objects.first()
        selected_teacher = StaffMember.objects.filter(pk=teacher_id).first() if teacher_id else None

        time_slots = TimeSlot.objects.filter(academic_year=academic_year).order_by('period_number') if academic_year else []
        days = [
            (1, 'Monday'),
            (2, 'Tuesday'),
            (3, 'Wednesday'),
            (4, 'Thursday'),
            (5, 'Friday'),
            (6, 'Saturday'),
        ]

        # Build 2D Schedule Grid: grid[day][slot] = entry
        grid = {}
        entries_qs = ClassTimetable.objects.filter(is_deleted=False).select_related('subject', 'teacher', 'section__class_level')
        
        if academic_year:
            entries_qs = entries_qs.filter(academic_year=academic_year)
            
        if selected_teacher:
            entries_qs = entries_qs.filter(teacher=selected_teacher)
        elif selected_section:
            entries_qs = entries_qs.filter(section=selected_section)

        entry_map = {(e.day_of_week, e.time_slot_id): e for e in entries_qs}

        for day_num, day_name in days:
            grid[day_num] = {
                'day_name': day_name,
                'slots': [{'slot': slot, 'entry': entry_map.get((day_num, slot.id))} for slot in time_slots]
            }

        context['academic_year'] = academic_year
        context['sections'] = Section.objects.filter(is_deleted=False).select_related('class_level')
        context['teachers'] = StaffMember.objects.filter(is_deleted=False, designation__is_teaching_role=True)
        context['selected_section'] = selected_section
        context['selected_teacher'] = selected_teacher
        context['time_slots'] = time_slots
        context['grid'] = grid
        context['days'] = days
        context['entry_form'] = ClassTimetableForm(initial={'academic_year': academic_year, 'section': selected_section})
        return context


class TimetableEntryCreateView(SchoolAdminRequiredMixin, CreateView):
    model = ClassTimetable
    form_class = ClassTimetableForm
    template_name = 'timetable/timetable_form.html'
    success_url = reverse_lazy('timetable:overview')

    def get_initial(self):
        initial = super().get_initial()
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        initial['academic_year'] = academic_year
        if self.request.GET.get('day'):
            initial['day_of_week'] = self.request.GET.get('day')
        if self.request.GET.get('slot'):
            initial['time_slot'] = self.request.GET.get('slot')
        if self.request.GET.get('section'):
            initial['section'] = self.request.GET.get('section')
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Timetable period allocated successfully.")
        return super().form_valid(form)


class TimetableEntryDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = ClassTimetable
    success_url = reverse_lazy('timetable:overview')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Timetable entry removed.")
        return super().delete(request, *args, **kwargs)


class TimeSlotListView(SchoolAdminRequiredMixin, ListView):
    model = TimeSlot
    template_name = 'timetable/timeslot_list.html'
    context_object_name = 'slots'

    def get_queryset(self):
        year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        return TimeSlot.objects.filter(academic_year=year) if year else TimeSlot.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TimeSlotForm()
        return context


class TimeSlotCreateView(SchoolAdminRequiredMixin, CreateView):
    model = TimeSlot
    form_class = TimeSlotForm
    template_name = 'timetable/timeslot_form.html'
    success_url = reverse_lazy('timetable:slot_list')

    def form_valid(self, form):
        messages.success(self.request, f"Period slot '{form.cleaned_data['name']}' created.")
        return super().form_valid(form)
