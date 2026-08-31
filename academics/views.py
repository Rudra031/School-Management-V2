from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from academics.models import AcademicYear, Department, ClassLevel, Section, Subject, ClassSubject, SubjectTeacherAllocation
from academics.forms import (
    AcademicYearForm, DepartmentForm, ClassLevelForm, SectionForm, SubjectForm, SubjectTeacherAllocationForm
)
from core.permissions import SchoolAdminRequiredMixin, AdminOrPrincipalRequiredMixin
from core.utils import log_audit
from core.models import AuditLog


class AcademicOverviewView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    Overview page for academic years, classes, sections, subjects, and departments.
    """
    template_name = 'academics/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.filter(is_deleted=False)
        context['departments'] = Department.objects.filter(is_deleted=False).prefetch_related('classes', 'subjects')
        context['classes'] = ClassLevel.objects.filter(is_deleted=False).prefetch_related('sections')
        context['subjects'] = Subject.objects.filter(is_deleted=False).select_related('department')
        context['allocations'] = SubjectTeacherAllocation.objects.filter(is_deleted=False).select_related('section__class_level', 'subject', 'teacher')
        return context


# ==============================================================================
# ACADEMIC YEARS
# ==============================================================================

class AcademicYearListView(AdminOrPrincipalRequiredMixin, ListView):
    model = AcademicYear
    template_name = 'academics/academic_year_list.html'
    context_object_name = 'years'
    queryset = AcademicYear.objects.filter(is_deleted=False)


class AcademicYearCreateView(SchoolAdminRequiredMixin, CreateView):
    model = AcademicYear
    form_class = AcademicYearForm
    template_name = 'academics/academic_year_form.html'
    success_url = reverse_lazy('academics:year_list')

    def form_valid(self, form):
        messages.success(self.request, f"Academic Year '{form.cleaned_data['name']}' created successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Academics',
            model_name='AcademicYear',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class AcademicYearUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = AcademicYear
    form_class = AcademicYearForm
    template_name = 'academics/academic_year_form.html'
    success_url = reverse_lazy('academics:year_list')

    def form_valid(self, form):
        messages.success(self.request, f"Academic Year '{self.object.name}' updated.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Academics',
            model_name='AcademicYear',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class AcademicYearSetActiveView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk):
        year = get_object_or_404(AcademicYear, pk=pk)
        year.is_current = True
        year.save()
        messages.success(request, f"'{year.name}' is now set as the active academic year.")
        return redirect('academics:year_list')


# ==============================================================================
# CLASSES & SECTIONS (ADD, EDIT, REMOVE)
# ==============================================================================

class ClassSectionManageView(AdminOrPrincipalRequiredMixin, TemplateView):
    template_name = 'academics/class_section_manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = ClassLevel.objects.filter(is_deleted=False).prefetch_related('sections__class_teacher')
        context['class_form'] = ClassLevelForm()
        context['section_form'] = SectionForm()
        return context


class ClassCreateView(SchoolAdminRequiredMixin, CreateView):
    model = ClassLevel
    form_class = ClassLevelForm
    template_name = 'academics/class_form.html'
    success_url = reverse_lazy('academics:class_manage')

    def form_valid(self, form):
        messages.success(self.request, f"Class Level '{form.cleaned_data['name']}' added successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Academics',
            model_name='ClassLevel',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class ClassUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = ClassLevel
    form_class = ClassLevelForm
    template_name = 'academics/class_form.html'
    success_url = reverse_lazy('academics:class_manage')

    def form_valid(self, form):
        messages.success(self.request, f"Class Level '{self.object.name}' updated successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Academics',
            model_name='ClassLevel',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class ClassDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = ClassLevel
    template_name = 'academics/class_confirm_delete.html'
    success_url = reverse_lazy('academics:class_manage')

    def form_valid(self, form):
        class_obj = self.get_object()
        class_name = class_obj.name
        # Soft delete sections belonging to this class
        class_obj.sections.all().update(is_deleted=True)
        class_obj.soft_delete()
        messages.warning(self.request, f"Class Level '{class_name}' and its associated sections have been removed.")
        log_audit(
            self.request,
            action=AuditLog.Action.DELETE,
            module='Academics',
            model_name='ClassLevel',
            object_id=str(class_obj.id),
            object_repr=class_name
        )
        return redirect(self.success_url)


class SectionCreateView(SchoolAdminRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = 'academics/section_form.html'
    success_url = reverse_lazy('academics:class_manage')

    def get_initial(self):
        initial = super().get_initial()
        class_id = self.request.GET.get('class_id')
        if class_id:
            initial['class_level'] = class_id
        return initial

    def form_valid(self, form):
        messages.success(self.request, f"Section '{form.cleaned_data['name']}' created successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Academics',
            model_name='Section',
            object_id=str(self.object.id),
            object_repr=self.object.full_name
        )
        return response


class SectionUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = 'academics/section_form.html'
    success_url = reverse_lazy('academics:class_manage')

    def form_valid(self, form):
        messages.success(self.request, f"Section '{self.object.full_name}' updated successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Academics',
            model_name='Section',
            object_id=str(self.object.id),
            object_repr=self.object.full_name
        )
        return response


class SectionDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = Section
    template_name = 'academics/section_confirm_delete.html'
    success_url = reverse_lazy('academics:class_manage')

    def form_valid(self, form):
        sec = self.get_object()
        sec_name = sec.full_name
        sec.soft_delete()
        messages.warning(self.request, f"Section '{sec_name}' has been removed.")
        log_audit(
            self.request,
            action=AuditLog.Action.DELETE,
            module='Academics',
            model_name='Section',
            object_id=str(sec.id),
            object_repr=sec_name
        )
        return redirect(self.success_url)


# ==============================================================================
# SUBJECTS (ADD, EDIT, REMOVE)
# ==============================================================================

class SubjectListView(AdminOrPrincipalRequiredMixin, ListView):
    model = Subject
    template_name = 'academics/subject_list.html'
    context_object_name = 'subjects'
    queryset = Subject.objects.filter(is_deleted=False).select_related('department')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SubjectForm()
        return context


class SubjectCreateView(SchoolAdminRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'academics/subject_form.html'
    success_url = reverse_lazy('academics:subject_list')

    def form_valid(self, form):
        messages.success(self.request, f"Subject '{form.cleaned_data['name']}' ({form.cleaned_data['code']}) created successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Academics',
            model_name='Subject',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class SubjectUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'academics/subject_form.html'
    success_url = reverse_lazy('academics:subject_list')

    def form_valid(self, form):
        messages.success(self.request, f"Subject '{self.object.name}' updated successfully.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='Academics',
            model_name='Subject',
            object_id=str(self.object.id),
            object_repr=self.object.name
        )
        return response


class SubjectDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = Subject
    template_name = 'academics/subject_confirm_delete.html'
    success_url = reverse_lazy('academics:subject_list')

    def form_valid(self, form):
        subj = self.get_object()
        subj_name = f"{subj.name} ({subj.code})"
        subj.soft_delete()
        messages.warning(self.request, f"Subject '{subj_name}' has been removed.")
        log_audit(
            self.request,
            action=AuditLog.Action.DELETE,
            module='Academics',
            model_name='Subject',
            object_id=str(subj.id),
            object_repr=subj_name
        )
        return redirect(self.success_url)


# ==============================================================================
# TEACHER ALLOCATIONS
# ==============================================================================

class TeacherAllocationView(AdminOrPrincipalRequiredMixin, ListView):
    model = SubjectTeacherAllocation
    template_name = 'academics/teacher_allocation.html'
    context_object_name = 'allocations'
    queryset = SubjectTeacherAllocation.objects.filter(is_deleted=False).select_related(
        'academic_year', 'section__class_level', 'subject', 'teacher'
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SubjectTeacherAllocationForm()
        return context


class TeacherAllocationCreateView(SchoolAdminRequiredMixin, CreateView):
    model = SubjectTeacherAllocation
    form_class = SubjectTeacherAllocationForm
    template_name = 'academics/teacher_allocation_form.html'
    success_url = reverse_lazy('academics:allocation_list')

    def form_valid(self, form):
        messages.success(self.request, "Subject teacher allocation saved successfully.")
        return super().form_valid(form)
