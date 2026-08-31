import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class GradeScale(BaseModel):
    """
    Configurable grading system scale (e.g. 90-100% -> A+, Grade Point 4.0).
    """
    name = models.CharField(max_length=50, default='Standard Letter Grade Scale')
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    grade_letter = models.CharField(max_length=10, help_text=_('e.g. A+, A, B, C, F'))
    grade_point = models.DecimalField(max_digits=4, decimal_places=2, default=0.00, help_text=_('e.g. 4.0, 3.5'))
    description = models.CharField(max_length=100, blank=True, help_text=_('e.g. Outstanding, Excellent, Fail'))

    class Meta:
        ordering = ['-min_percentage']
        verbose_name = _('Grade Scale')
        verbose_name_plural = _('Grade Scales')

    def __str__(self):
        return f"{self.grade_letter} ({self.min_percentage}% - {self.max_percentage}%)"

    @classmethod
    def get_grade_for_percentage(cls, percentage):
        scale = cls.objects.filter(
            min_percentage__lte=percentage,
            max_percentage__gte=percentage
        ).first()
        return scale


class ExamTerm(BaseModel):
    """
    Examination Cycle / Term (e.g. Term 1 Midterms 2026, Final Board Exams 2027).
    """
    class TermType(models.TextChoices):
        UNIT_TEST = 'UNIT_TEST', _('Unit Test / Periodic Assessment')
        QUARTERLY = 'QUARTERLY', _('Quarterly Examination')
        HALF_YEARLY = 'HALF_YEARLY', _('Term 1 / Half-Yearly')
        PRE_BOARD = 'PRE_BOARD', _('Pre-Board Examination')
        ANNUAL = 'ANNUAL', _('Term 2 / Annual Final Examination')

    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='exam_terms')
    title = models.CharField(max_length=100, help_text=_('e.g. Term 1 Examinations'))
    term_type = models.CharField(max_length=20, choices=TermType.choices, default=TermType.HALF_YEARLY)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False, help_text=_('Report cards accessible to parents/students once published'))
    admit_card_published = models.BooleanField(default=True, help_text=_('Hall tickets available for download/print'))
    requires_fee_clearance = models.BooleanField(
        default=False,
        help_text=_('Require fee clearance up to current term before issuing Admit Cards or publishing results')
    )
    pass_percentage_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=33.00, help_text=_('Minimum passing percentage (e.g. 33% / 35%)'))

    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Exam Term')
        verbose_name_plural = _('Exam Terms')

    def __str__(self):
        return f"{self.title} - {self.get_term_type_display()} ({self.academic_year.name})"


class ExamSchedule(BaseModel):
    """
    Subject-wise exam date, duration, room, and multi-component maximum marks.
    """
    exam_term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name='schedules')
    class_level = models.ForeignKey('academics.ClassLevel', on_delete=models.CASCADE, related_name='exam_schedules')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='exam_schedules')
    exam_date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=180)
    room_number = models.CharField(max_length=50, blank=True, default='Hall A-1')
    exam_center = models.CharField(max_length=100, blank=True, default='Main Academic Campus')
    instructions = models.TextField(blank=True, default='Carry your Admit Card and institutional ID card. No electronic gadgets permitted.')
    
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    pass_marks = models.DecimalField(max_digits=5, decimal_places=2, default=33.00)
    theory_marks_max = models.DecimalField(max_digits=5, decimal_places=2, default=80.00)
    practical_marks_max = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    internal_marks_max = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, help_text=_('Internal Assessment / Periodic Test / Portfolio'))

    class Meta:
        ordering = ['exam_date', 'start_time']
        unique_together = ('exam_term', 'class_level', 'subject')
        verbose_name = _('Exam Schedule')
        verbose_name_plural = _('Exam Schedules')

    def __str__(self):
        return f"{self.exam_term.title} | {self.class_level.name} - {self.subject.name}"


class ExamMarkEntry(BaseModel):
    """
    Individual student multi-component score entry for a scheduled exam.
    """
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='marks')
    student_enrollment = models.ForeignKey('students.StudentEnrollment', on_delete=models.CASCADE, related_name='exam_marks')
    
    theory_marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    practical_marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    internal_marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    grace_marks = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    total_marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    grade = models.ForeignKey(GradeScale, on_delete=models.SET_NULL, null=True, blank=True, related_name='exam_entries')
    is_absent = models.BooleanField(default=False)
    is_medical_leave = models.BooleanField(default=False)
    remarks = models.CharField(max_length=255, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_exam_marks'
    )

    class Meta:
        ordering = ['student_enrollment__roll_number']
        unique_together = ('exam_schedule', 'student_enrollment')
        verbose_name = _('Exam Mark Entry')
        verbose_name_plural = _('Exam Mark Entries')

    def __str__(self):
        return f"{self.student_enrollment.student.full_name} - {self.exam_schedule.subject.name}: {self.total_marks_obtained}/{self.exam_schedule.max_marks}"

    @property
    def percentage(self):
        if self.is_absent or self.is_medical_leave or self.exam_schedule.max_marks <= 0:
            return Decimal('0.00')
        return round((self.total_marks_obtained / self.exam_schedule.max_marks) * 100, 2)

    @property
    def is_passed(self):
        if self.is_absent or self.is_medical_leave:
            return False
        return self.total_marks_obtained >= self.exam_schedule.pass_marks

    def save(self, *args, **kwargs):
        # Auto-compute total marks
        if not self.is_absent and not self.is_medical_leave:
            th = Decimal(str(self.theory_marks_obtained or '0.00'))
            pr = Decimal(str(self.practical_marks_obtained or '0.00'))
            ia = Decimal(str(self.internal_marks_obtained or '0.00'))
            gr = Decimal(str(self.grace_marks or '0.00'))
            self.theory_marks_obtained = th
            self.practical_marks_obtained = pr
            self.internal_marks_obtained = ia
            self.grace_marks = gr
            self.total_marks_obtained = th + pr + ia + gr
            
            # Resolve grade letter
            pct = self.percentage
            scale = GradeScale.get_grade_for_percentage(pct)
            if scale:
                self.grade = scale
        else:
            self.total_marks_obtained = Decimal('0.00')
        super().save(*args, **kwargs)

