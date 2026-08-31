from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.utils import timezone

from assignments.models import Assignment, AssignmentSubmission
from assignments.forms import AssignmentForm, AssignmentSubmissionForm, AssignmentGradingForm
from academics.models import AcademicYear, Section, Subject
from staff.models import StaffMember
from core.permissions import TeacherRequiredMixin, StudentRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class AssignmentListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    model = Assignment
    template_name = 'assignments/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        qs = Assignment.objects.filter(is_deleted=False).select_related('section__class_level', 'subject', 'teacher')
        
        # If student, show only their enrolled section assignments
        if self.request.user.is_student:
            student = getattr(self.request.user, 'student_profile', None)
            if student and student.current_enrollment:
                qs = qs.filter(section=student.current_enrollment.section, status=Assignment.Status.PUBLISHED)
        elif self.request.user.is_teacher and not self.request.user.is_superadmin:
            staff = getattr(self.request.user, 'staff_profile', None)
            if staff:
                qs = qs.filter(teacher=staff)

        section_id = self.request.GET.get('section')
        subject_id = self.request.GET.get('subject')
        if section_id:
            qs = qs.filter(section_id=section_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sections'] = Section.objects.filter(is_deleted=False).select_related('class_level')
        context['subjects'] = Subject.objects.filter(is_deleted=False)
        return context


class AssignmentDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    model = Assignment
    template_name = 'assignments/assignment_detail.html'
    context_object_name = 'assignment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submissions'] = self.object.submissions.filter(is_deleted=False).select_related('student_enrollment__student')
        
        # Check if student viewing own submission
        user_submission = None
        if self.request.user.is_student:
            student = getattr(self.request.user, 'student_profile', None)
            if student and student.current_enrollment:
                user_submission = self.object.submissions.filter(student_enrollment=student.current_enrollment).first()
        context['user_submission'] = user_submission
        context['submission_form'] = AssignmentSubmissionForm(instance=user_submission)
        return context


class AssignmentCreateView(TeacherRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'
    success_url = reverse_lazy('assignments:list')

    def form_valid(self, form):
        assignment = form.save(commit=False)
        staff = getattr(self.request.user, 'staff_profile', None)
        if staff:
            assignment.teacher = staff
        else:
            # Fallback if admin creates
            assignment.teacher = StaffMember.objects.filter(designation__is_teaching_role=True).first()
        assignment.save()
        messages.success(self.request, f"Assignment '{assignment.title}' created and published.")
        return redirect('assignments:list')


class AssignmentSubmitView(StudentRequiredMixin, View):
    """
    Student homework submission endpoint.
    """
    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        student = getattr(request.user, 'student_profile', None)
        if not student or not student.current_enrollment:
            messages.error(request, "Active student enrollment record required to submit work.")
            return redirect('assignments:detail', pk=pk)

        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student_enrollment=student.current_enrollment,
        )
        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            if timezone.now() > assignment.due_date:
                sub.status = AssignmentSubmission.Status.LATE
            else:
                sub.status = AssignmentSubmission.Status.SUBMITTED
            sub.save()
            messages.success(request, "Homework submitted successfully.")
        else:
            messages.error(request, "Error submitting work. Please check the file.")
        return redirect('assignments:detail', pk=pk)


class AssignmentGradeSubmissionView(TeacherRequiredMixin, View):
    """
    Teacher grading endpoint for an individual submission.
    """
    def post(self, request, pk):
        submission = get_object_or_404(AssignmentSubmission, pk=pk)
        form = AssignmentGradingForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.graded_by = request.user
            sub.graded_at = timezone.now()
            sub.status = AssignmentSubmission.Status.GRADED
            sub.save()
            messages.success(request, f"Submission for {sub.student_enrollment.student.full_name} graded successfully.")
        return redirect('assignments:detail', pk=submission.assignment.pk)
