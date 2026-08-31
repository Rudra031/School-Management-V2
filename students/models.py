import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class Student(BaseModel):
    """
    Student Master Identity Record.
    Stores permanent demographic, contact, and identity information.
    """
    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active Enrolled')
        GRADUATED = 'GRADUATED', _('Graduated / Alumni')
        TRANSFERRED = 'TRANSFERRED', _('Transferred Out')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        DROPOUT = 'DROPOUT', _('Withdrawn / Dropped Out')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile'
    )
    admission_number = models.CharField(max_length=50, unique=True, db_index=True)
    student_id = models.CharField(max_length=50, unique=True, db_index=True, help_text=_('Unique Student Identification Number'))
    
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField()
    national_id_number = models.CharField(max_length=100, blank=True, help_text=_('National ID / Birth Certificate No.'))
    photo = models.ImageField(upload_to='students/photos/%Y/', blank=True, null=True)
    
    admission_date = models.DateField()
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-')
        ],
        blank=True
    )
    religion = models.CharField(max_length=50, blank=True)
    caste_category = models.CharField(max_length=50, blank=True, default='General')
    nationality = models.CharField(max_length=50, blank=True, default='United States')
    
    # Contact & Residential Details
    residential_address = models.TextField()
    permanent_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True, default='Metro City')
    state = models.CharField(max_length=100, blank=True, default='State')
    postal_code = models.CharField(max_length=20, blank=True, default='100001')
    
    # Emergency Contacts
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=50)
    emergency_contact_relation = models.CharField(max_length=50, help_text=_('e.g. Father, Mother, Uncle'))
    
    # Previous Academic Record
    previous_school_name = models.CharField(max_length=200, blank=True)
    previous_school_tc_number = models.CharField(max_length=100, blank=True, help_text=_('Transfer Certificate No.'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ['admission_number']
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        indexes = [
            models.Index(fields=['admission_number', 'status']),
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p]).strip()

    @property
    def current_enrollment(self):
        return self.enrollments.filter(is_current=True, is_deleted=False).select_related('section__class_level', 'academic_year').first()

    @property
    def current_class_section(self):
        enrollment = self.current_enrollment
        return enrollment.section.full_name if enrollment else "Unassigned"


class StudentEnrollment(BaseModel):
    """
    Historical & Current Placement Record.
    Connects a Student to a Section, Academic Year, and Roll Number.
    """
    class PromotionStatus(models.TextChoices):
        ENROLLED = 'ENROLLED', _('Currently Enrolled')
        PROMOTED = 'PROMOTED', _('Promoted to Next Grade')
        RETAINED = 'RETAINED', _('Retained / Repeated')
        DETACHED = 'DETACHED', _('Detached / Completed')

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='student_enrollments')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='enrollments')
    roll_number = models.PositiveIntegerField(help_text=_('Roll number within section for the academic year'))
    enrollment_date = models.DateField(default=timezone.now)
    is_current = models.BooleanField(default=True, help_text=_('Indicates active enrollment for current session'))
    promotion_status = models.CharField(max_length=20, choices=PromotionStatus.choices, default=PromotionStatus.ENROLLED)

    class Meta:
        ordering = ['section', 'roll_number']
        unique_together = (
            ('academic_year', 'section', 'roll_number'),
            ('student', 'academic_year'),
        )
        verbose_name = _('Student Enrollment')
        verbose_name_plural = _('Student Enrollments')
        indexes = [
            models.Index(fields=['academic_year', 'section', 'is_current']),
            models.Index(fields=['student', 'is_current']),
        ]

    def __str__(self):
        return f"{self.student.full_name} | {self.section} | Roll #{self.roll_number} ({self.academic_year.name})"

    def save(self, *args, **kwargs):
        if self.is_current:
            # Demote any other current enrollments for this student
            StudentEnrollment.objects.filter(student=self.student, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class StudentHealthRecord(BaseModel):
    """
    Confidential Medical and Health Information for a Student.
    Access is strictly restricted to authorized staff/nurse/principal.
    """
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='health_record')
    blood_group = models.CharField(max_length=5, blank=True)
    allergies_summary = models.TextField(blank=True, help_text=_('Food, drug, or environmental allergies'))
    chronic_conditions = models.TextField(blank=True, help_text=_('e.g. Asthma, Diabetes, Epilepsy'))
    medications = models.TextField(blank=True, help_text=_('Regular prescriptions or emergency meds'))
    dietary_restrictions = models.TextField(blank=True, help_text=_('Vegetarian, Halal, Nut-free, etc.'))
    
    doctor_name = models.CharField(max_length=100, blank=True)
    doctor_phone = models.CharField(max_length=50, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    additional_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Student Health Record')
        verbose_name_plural = _('Student Health Records')

    def __str__(self):
        return f"Health Record - {self.student.full_name}"


class StudentMedicalIncident(BaseModel):
    """
    Medical or First-Aid Incidents occurring on campus.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='medical_incidents')
    incident_date = models.DateTimeField()
    title = models.CharField(max_length=200, help_text=_('e.g. Sports Injury, Fever, Allergic Reaction'))
    description = models.TextField()
    treatment_given = models.TextField()
    referred_to_hospital = models.BooleanField(default=False)
    hospital_name = models.CharField(max_length=200, blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_medical_incidents'
    )

    class Meta:
        ordering = ['-incident_date']
        verbose_name = _('Medical Incident')
        verbose_name_plural = _('Medical Incidents')

    def __str__(self):
        return f"[{self.incident_date.strftime('%Y-%m-%d')}] {self.student.full_name} - {self.title}"
