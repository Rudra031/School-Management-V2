import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class AcademicYear(BaseModel):
    """
    Academic Session / Year (e.g. 2025-2026).
    Only one academic year should have is_current=True at a given time.
    """
    name = models.CharField(max_length=50, unique=True, help_text=_('e.g. 2025-2026'))
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, help_text=_('Designates active academic session'))
    is_closed = models.BooleanField(default=False, help_text=_('Closed academic years cannot be modified'))

    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Academic Year')
        verbose_name_plural = _('Academic Years')

    def __str__(self):
        return f"{self.name}{' (Current)' if self.is_current else ''}"

    def save(self, *args, **kwargs):
        if self.is_current:
            # Set all other academic years is_current to False
            AcademicYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Department(BaseModel):
    """
    Academic Department (e.g. Science, Mathematics, Humanities, Languages).
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text=_('e.g. SCI, MATH, HUM'))
    head_of_department = models.ForeignKey(
        'staff.StaffMember',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassLevel(BaseModel):
    """
    Grade / Class Level (e.g. Grade 1, Grade 10).
    """
    name = models.CharField(max_length=50, unique=True, help_text=_('e.g. Grade 10'))
    numeric_level = models.PositiveSmallIntegerField(unique=True, help_text=_('Numeric representation for sorting/promotion, e.g. 10'))
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['numeric_level']
        verbose_name = _('Class Level')
        verbose_name_plural = _('Class Levels')

    def __str__(self):
        return self.name

    @property
    def total_sections(self):
        return self.sections.filter(is_deleted=False).count()


class Section(BaseModel):
    """
    Section within a Class (e.g. Grade 10 - Section A).
    """
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=20, help_text=_('e.g. A, B, Rose, Daisy'))
    room_number = models.CharField(max_length=50, blank=True)
    class_teacher = models.ForeignKey(
        'staff.StaffMember',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_class_sections'
    )
    max_capacity = models.PositiveIntegerField(default=40)

    class Meta:
        ordering = ['class_level__numeric_level', 'name']
        unique_together = ('class_level', 'name')
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')

    def __str__(self):
        return f"{self.class_level.name} - Section {self.name}"

    @property
    def full_name(self):
        return f"{self.class_level.name} ({self.name})"

    @property
    def active_student_count(self):
        return self.enrollments.filter(is_current=True, is_deleted=False).count()


class Subject(BaseModel):
    """
    Subject taught in the school curriculum (e.g. Mathematics, Physics, English).
    """
    class SubjectType(models.TextChoices):
        THEORY = 'THEORY', _('Theory Only')
        PRACTICAL = 'PRACTICAL', _('Practical Only')
        BOTH = 'BOTH', _('Theory & Practical')
        OPTIONAL = 'OPTIONAL', _('Optional / Elective')

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text=_('e.g. MATH-101'))
    subject_type = models.CharField(max_length=20, choices=SubjectType.choices, default=SubjectType.THEORY)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects')
    credit_hours = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassSubject(BaseModel):
    """
    Maps Subjects to a Class Level with credit and pass marks definitions.
    """
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='class_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='class_allocations')
    is_elective = models.BooleanField(default=False)
    pass_marks = models.DecimalField(max_digits=5, decimal_places=2, default=35.0)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)

    class Meta:
        unique_together = ('class_level', 'subject')
        verbose_name = _('Class Subject')
        verbose_name_plural = _('Class Subjects')

    def __str__(self):
        return f"{self.class_level.name} - {self.subject.name}"


class SubjectTeacherAllocation(BaseModel):
    """
    Allocates a Teacher to teach a specific Subject in a specific Section for an Academic Year.
    """
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='teacher_allocations')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='teacher_allocations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='teacher_allocations')
    teacher = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, related_name='subject_allocations')

    class Meta:
        unique_together = ('academic_year', 'section', 'subject', 'teacher')
        verbose_name = _('Subject Teacher Allocation')
        verbose_name_plural = _('Subject Teacher Allocations')

    def __str__(self):
        return f"{self.section} | {self.subject.name} - {self.teacher.full_name} ({self.academic_year.name})"
