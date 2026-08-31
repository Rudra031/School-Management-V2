import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class Assignment(BaseModel):
    """
    Homework or class assignment created by a teacher for a class section.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PUBLISHED = 'PUBLISHED', _('Published')
        CLOSED = 'CLOSED', _('Closed')

    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='assignments')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='assignments')
    teacher = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, related_name='assignments')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    attachment_file = models.FileField(upload_to='assignments/attachments/%Y/', blank=True, null=True)
    assigned_date = models.DateField()
    due_date = models.DateTimeField()
    max_points = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)

    class Meta:
        ordering = ['-due_date', '-created_at']
        verbose_name = _('Assignment')
        verbose_name_plural = _('Assignments')

    def __str__(self):
        return f"{self.title} | {self.section} ({self.subject.name})"

    @property
    def total_submissions(self):
        return self.submissions.count()

    @property
    def graded_submissions(self):
        return self.submissions.filter(status=AssignmentSubmission.Status.GRADED).count()


class AssignmentSubmission(BaseModel):
    """
    Student homework file submission and teacher evaluation.
    """
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Submitted')
        LATE = 'LATE', _('Submitted Late')
        GRADED = 'GRADED', _('Graded')
        RESUBMIT_REQUESTED = 'RESUBMIT_REQUESTED', _('Resubmission Requested')

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student_enrollment = models.ForeignKey('students.StudentEnrollment', on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_file = models.FileField(upload_to='assignments/submissions/%Y/', blank=True, null=True)
    submission_text = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    
    score_obtained = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_homework'
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('assignment', 'student_enrollment')
        verbose_name = _('Assignment Submission')
        verbose_name_plural = _('Assignment Submissions')

    def __str__(self):
        return f"{self.student_enrollment.student.full_name} -> {self.assignment.title} ({self.get_status_display()})"
