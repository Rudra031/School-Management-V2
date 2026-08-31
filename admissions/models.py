import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class AdmissionsApplication(BaseModel):
    """
    Prospective student admission enquiry and application tracking pipeline.
    """
    class Stage(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Application Submitted')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        SHORTLISTED = 'SHORTLISTED', _('Shortlisted')
        ENTRANCE_SCHEDULED = 'ENTRANCE_SCHEDULED', _('Entrance Exam / Interview Scheduled')
        ACCEPTED = 'ACCEPTED', _('Accepted / Approved')
        REJECTED = 'REJECTED', _('Rejected')
        ENROLLED = 'ENROLLED', _('Enrolled as Student')

    application_number = models.CharField(max_length=50, unique=True, db_index=True)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='admission_applications')
    applying_for_class = models.ForeignKey('academics.ClassLevel', on_delete=models.CASCADE, related_name='admission_applications')
    
    # Applicant Demographics
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(
        max_length=10,
        choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')]
    )
    date_of_birth = models.DateField()
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
    caste_category = models.CharField(max_length=50, blank=True, default='General')
    aadhaar_number = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='admissions/photos/%Y/', blank=True, null=True)
    
    # Parent / Family Details
    parent_name = models.CharField(max_length=150)
    parent_phone = models.CharField(max_length=30)
    parent_email = models.EmailField()
    father_name = models.CharField(max_length=150, blank=True)
    father_phone = models.CharField(max_length=30, blank=True)
    father_occupation = models.CharField(max_length=100, blank=True)
    mother_name = models.CharField(max_length=150, blank=True)
    mother_phone = models.CharField(max_length=30, blank=True)
    mother_occupation = models.CharField(max_length=100, blank=True)
    residential_address = models.TextField()
    city = models.CharField(max_length=100, blank=True, default='Kolkata')
    state = models.CharField(max_length=100, blank=True, default='West Bengal')
    pin_code = models.CharField(max_length=20, blank=True)

    # Academic Background & Senior Stream Preference
    stream_preference = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('SCIENCE_PCM', 'Science (Physics, Chemistry, Mathematics)'),
            ('SCIENCE_PCB', 'Science (Physics, Chemistry, Biology)'),
            ('COMMERCE', 'Commerce with Mathematics / Informatics'),
            ('HUMANITIES', 'Humanities / Arts & Legal Studies')
        ]
    )
    previous_school = models.CharField(max_length=200, blank=True)
    previous_board = models.CharField(max_length=100, blank=True, default='CBSE')
    previous_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tc_status = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('ATTACHED', 'Transfer Certificate Attached'),
            ('WILL_SUBMIT', 'Will Submit Prior to Final Admission'),
            ('NOT_APPLICABLE', 'Not Applicable (Fresh Admission to Nursery)')
        ],
        default='WILL_SUBMIT'
    )

    # Sibling Details
    has_sibling_in_school = models.BooleanField(default=False)
    sibling_details = models.CharField(max_length=255, blank=True, help_text='Name, Admission No, and Class of Sibling')
    
    # Pipeline Status
    status = models.CharField(max_length=30, choices=Stage.choices, default=Stage.SUBMITTED)
    applied_date = models.DateField(default=timezone.now)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_admissions'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-applied_date', '-created_at']
        verbose_name = _('Admission Application')
        verbose_name_plural = _('Admission Applications')

    def __str__(self):
        return f"{self.application_number} - {self.first_name} {self.last_name} ({self.get_status_display()})"

    @property
    def applicant_full_name(self):
        return f"{self.first_name} {self.last_name}"
