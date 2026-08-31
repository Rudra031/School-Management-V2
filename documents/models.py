import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class DocumentCategory(BaseModel):
    """
    Document Categorization (e.g. Identity Proofs, Transfer Certificates, Transcripts, Circulars).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Document Category')
        verbose_name_plural = _('Document Categories')

    def __str__(self):
        return self.name


class SchoolDocument(BaseModel):
    """
    Centralized Institutional Document Repository.
    """
    class AccessLevel(models.TextChoices):
        PUBLIC = 'PUBLIC', _('Public / All Users')
        STAFF_ONLY = 'STAFF_ONLY', _('Staff & Faculty Only')
        RESTRICTED_ADMIN = 'RESTRICTED_ADMIN', _('Restricted Administrators Only')
        PARENT_ACCESSIBLE = 'PARENT_ACCESSIBLE', _('Accessible to Parents & Students')

    title = models.CharField(max_length=200)
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    document_file = models.FileField(upload_to='documents/repository/%Y/%m/')
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, null=True, blank=True, related_name='attached_documents')
    staff_member = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, null=True, blank=True, related_name='attached_documents')
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    access_level = models.CharField(max_length=30, choices=AccessLevel.choices, default=AccessLevel.STAFF_ONLY)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('School Document')
        verbose_name_plural = _('School Documents')

    def __str__(self):
        return f"{self.title} ({self.get_access_level_display()})"


class CertificateType(models.TextChoices):
    TRANSFER_CERTIFICATE = 'TC', _('Transfer Certificate (TC)')
    CHARACTER_CERTIFICATE = 'CHARACTER', _('Character Certificate')
    BONAFIDE_CERTIFICATE = 'BONAFIDE', _('Bonafide / Study Certificate')
    FEE_CLEARANCE = 'FEE_CLEARANCE', _('Fee Clearance (No Dues) Certificate')
    MIGRATION = 'MIGRATION', _('Migration Certificate')
    CUSTOM = 'CUSTOM', _('Special / Custom Certificate')


class CertificateTemplate(BaseModel):
    """
    Configurable certificate template definitions.
    """
    name = models.CharField(max_length=150)
    certificate_type = models.CharField(max_length=30, choices=CertificateType.choices, default=CertificateType.TRANSFER_CERTIFICATE)
    header_title = models.CharField(max_length=200, default='TRANSFER CERTIFICATE')
    sub_header = models.CharField(max_length=255, blank=True, default='(Affiliated to CBSE, New Delhi | Affiliation No: 2130894 | School Code: 70123)')
    body_template = models.TextField(blank=True, help_text=_('HTML or text blueprint for certificate body'))
    footer_note = models.TextField(blank=True, default='Certified that the above information is in accordance with the School General Register.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['certificate_type', 'name']
        verbose_name = _('Certificate Template')
        verbose_name_plural = _('Certificate Templates')

    def __str__(self):
        return f"{self.get_certificate_type_display()} - {self.name}"


class IssuedCertificate(BaseModel):
    """
    Official Issued Student Certificate Record with verifiable cryptographic token.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ISSUED = 'ISSUED', _('Issued')
        REVOKED = 'REVOKED', _('Revoked / Cancelled')

    certificate_number = models.CharField(max_length=80, unique=True, db_index=True)
    book_number = models.CharField(max_length=40, blank=True, default='B-01')
    serial_number = models.CharField(max_length=40, blank=True, default='001')
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    
    certificate_type = models.CharField(max_length=30, choices=CertificateType.choices, default=CertificateType.TRANSFER_CERTIFICATE)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='issued_certificates')
    student_enrollment = models.ForeignKey('students.StudentEnrollment', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_certificates')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_certificates')
    
    issue_date = models.DateField()
    leaving_date = models.DateField(null=True, blank=True)
    reason_for_leaving = models.CharField(max_length=255, default='Completed Course / Higher Studies')
    general_conduct = models.CharField(max_length=100, default='Good')
    
    dues_cleared = models.BooleanField(default=True, help_text=_('Whether all school fee dues have been fully settled'))
    total_working_days = models.PositiveIntegerField(default=220)
    total_present_days = models.PositiveIntegerField(default=205)
    last_class_passed = models.CharField(max_length=100, blank=True)
    qualified_for_promotion = models.BooleanField(default=True)
    ncc_cadet_or_scout = models.CharField(max_length=100, blank=True, default='N/A')
    games_played = models.CharField(max_length=255, blank=True, default='Regular participation in school sports')
    
    custom_remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    
    is_revoked = models.BooleanField(default=False)
    revocation_reason = models.CharField(max_length=255, blank=True)
    
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_school_certificates'
    )

    class Meta:
        ordering = ['-issue_date', '-created_at']
        verbose_name = _('Issued Certificate')
        verbose_name_plural = _('Issued Certificates')

    def __str__(self):
        return f"{self.certificate_number} - {self.student.full_name} ({self.get_certificate_type_display()})"


class IDCardOrientation(models.TextChoices):
    PORTRAIT = 'PORTRAIT', _('Portrait (Standard 54x86mm Badge)')
    LANDSCAPE = 'LANDSCAPE', _('Landscape (Standard 86x54mm Badge)')


class IDCardTheme(models.TextChoices):
    NAVY_GOLD = 'NAVY_GOLD', _('Academic Navy & Gold (#1E1B4B / #D4AF37)')
    EMERALD = 'EMERALD', _('Prestige Emerald (#006C49 / #10B981)')
    MAROON = 'MAROON', _('Royal Maroon (#7E1D1D / #F59E0B)')
    INDIGO_VIOLET = 'INDIGO_VIOLET', _('Modern Indigo & Violet (#4F46E5 / #8B5CF6)')


class IDCardConfiguration(BaseModel):
    """
    ID Card Visual Styling and Formatting Settings.
    """
    name = models.CharField(max_length=100, unique=True)
    orientation = models.CharField(max_length=20, choices=IDCardOrientation.choices, default=IDCardOrientation.PORTRAIT)
    theme = models.CharField(max_length=30, choices=IDCardTheme.choices, default=IDCardTheme.NAVY_GOLD)
    primary_color = models.CharField(max_length=20, default='#1E1B4B')
    accent_color = models.CharField(max_length=20, default='#D4AF37')
    
    show_blood_group = models.BooleanField(default=True)
    show_emergency_contact = models.BooleanField(default=True)
    show_residential_address = models.BooleanField(default=True)
    show_bus_route = models.BooleanField(default=True)
    show_barcode = models.BooleanField(default=True)
    show_qr_code = models.BooleanField(default=True)
    
    return_policy_text = models.TextField(
        default='If found, please return to School Administration Office. Apex International Academy, Sector 12, Dwarka, New Delhi. Helpline: +91 11 2659 8000'
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name = _('ID Card Configuration')
        verbose_name_plural = _('ID Card Configurations')

    def __str__(self):
        return f"{self.name} ({self.get_orientation_display()})"


class IssuedIDCard(BaseModel):
    """
    Student or Staff Issued Physical ID Card Badge Record.
    """
    class CardType(models.TextChoices):
        STUDENT = 'STUDENT', _('Student ID Card')
        STAFF = 'STAFF', _('Staff & Faculty ID Card')

    card_number = models.CharField(max_length=60, unique=True, db_index=True)
    card_type = models.CharField(max_length=20, choices=CardType.choices, default=CardType.STUDENT)
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, null=True, blank=True, related_name='id_cards')
    staff_member = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, null=True, blank=True, related_name='id_cards')
    config = models.ForeignKey(IDCardConfiguration, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_cards')
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.SET_NULL, null=True, blank=True, related_name='id_cards')
    
    issue_date = models.DateField()
    valid_until = models.DateField()
    barcode_data = models.CharField(max_length=100, blank=True)
    qr_data = models.CharField(max_length=255, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_printed = models.BooleanField(default=False)
    print_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-issue_date', '-created_at']
        verbose_name = _('Issued ID Card')
        verbose_name_plural = _('Issued ID Cards')

    def __str__(self):
        holder = self.student.full_name if self.student else (self.staff_member.full_name if self.staff_member else 'Unknown')
        return f"{self.card_number} - {holder} ({self.get_card_type_display()})"

