import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    """
    Abstract base model providing self-updating created_at and updated_at fields,
    along with soft-delete support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])


class SchoolSetting(models.Model):
    """
    Singleton model holding configurable global school information and settings.
    No hardcoded values.
    """
    name = models.CharField(max_length=200, default='Horizon Public School')
    code = models.CharField(max_length=50, default='HPS-DELHI', help_text=_('Unique school registration code'))
    tagline = models.CharField(max_length=255, blank=True, default='Affiliated to CBSE, New Delhi (Affiliation No. 2130894)')
    logo = models.ImageField(upload_to='school/branding/', blank=True, null=True)
    favicon = models.ImageField(upload_to='school/branding/', blank=True, null=True)
    
    # Contact & Location
    address = models.TextField(blank=True, default='Sector 14, Urban Estate, Rohini')
    city = models.CharField(max_length=100, blank=True, default='New Delhi')
    state = models.CharField(max_length=100, blank=True, default='Delhi (NCT)')
    postal_code = models.CharField(max_length=20, blank=True, default='110085')
    country = models.CharField(max_length=100, blank=True, default='India')
    phone = models.CharField(max_length=50, blank=True, default='+91 (011) 2748-9012 / +91 98765 43210')
    email = models.EmailField(blank=True, default='admissions@horizonpublicschool.edu.in')
    website = models.URLField(blank=True, default='https://horizonpublicschool.edu.in')
    
    # Financial & Localization
    currency_symbol = models.CharField(max_length=10, default='₹')
    currency_code = models.CharField(max_length=10, default='INR')
    date_format = models.CharField(
        max_length=20, 
        default='d M Y', 
        choices=[
            ('d M Y', '26 Aug 2026 (d M Y)'),
            ('Y-m-d', '2026-08-26 (Y-m-d)'),
            ('d/m/Y', '26/08/2026 (d/m/Y)'),
            ('m/d/Y', '08/26/2026 (m/d/Y)'),
        ]
    )
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    # Academic & Operational Policies
    attendance_threshold_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=75.00,
        help_text=_('Minimum required attendance percentage for exam eligibility')
    )
    enable_student_login = models.BooleanField(default=True)
    enable_parent_login = models.BooleanField(default=True)
    enable_online_admissions = models.BooleanField(default=True)

    # --------------------------------------------------------------------------
    # 1. Rules, Regulations & Student Code of Conduct
    # --------------------------------------------------------------------------
    discipline_policy = models.TextField(
        blank=True,
        default='Students must uphold the highest standards of integrity, punctuality, and mutual respect. Bullying, ragging, vandalism, or possession of unauthorized items is strictly prohibited under institutional POCSO & CBSE bylaws.'
    )
    uniform_policy = models.TextField(
        blank=True,
        default='Summer: Monday to Friday standard blue crest uniform with black polished shoes. Winter: Navy blazer with school tie and pullover. School ID Card Badge is mandatory at all times.'
    )
    mobile_device_policy = models.CharField(
        max_length=50,
        choices=[
            ('PROHIBITED', 'Strictly Prohibited on Campus'),
            ('LOCKER_DEPOSITED', 'Allowed with Morning Locker Deposit'),
            ('CLASSROOM_PERMITTED', 'Permitted for Digital Smart Learning')
        ],
        default='LOCKER_DEPOSITED'
    )
    late_coming_grace_minutes = models.PositiveIntegerField(
        default=10,
        help_text=_('Grace period (in minutes) after morning assembly bell')
    )
    late_marks_for_half_day = models.PositiveIntegerField(
        default=3,
        help_text=_('Number of late arrival marks that convert to 1 half-day leave')
    )
    consecutive_absence_warning_days = models.PositiveIntegerField(
        default=3,
        help_text=_('Days of unexcused absence before auto-generating parent warning notice')
    )
    medical_leave_cert_threshold_days = models.PositiveIntegerField(
        default=3,
        help_text=_('Leaves exceeding these consecutive days require registered MBBS doctor certificate')
    )
    late_fee_per_day = models.DecimalField(
        max_digits=8, decimal_places=2, default=20.00,
        help_text=_('Per-day fine levied after fee submission due date')
    )
    fee_due_day_of_month = models.PositiveIntegerField(
        default=10,
        help_text=_('Day of month (1-31) after which late fine starts calculating')
    )
    sibling_concession_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.00,
        help_text=_('Standard concession percentage for 2nd/3rd sibling')
    )
    passing_marks_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=33.00,
        help_text=_('Minimum passing percentage per subject (CBSE Standard)')
    )
    ptm_visiting_hours = models.CharField(
        max_length=255, blank=True,
        default='2nd Saturday: 09:00 AM - 01:00 PM | Weekdays by prior appointment: 02:30 PM - 03:30 PM'
    )
    grievance_escalation_matrix = models.TextField(
        blank=True,
        default='Level 1: Class Teacher -> Level 2: Section Coordinator -> Level 3: Vice Principal -> Level 4: Principal / Management'
    )

    # --------------------------------------------------------------------------
    # 2. Board Affiliation & Legal Master
    # --------------------------------------------------------------------------
    board_name = models.CharField(
        max_length=50,
        choices=[
            ('CBSE', 'Central Board of Secondary Education (CBSE)'),
            ('ICSE', 'Council for the Indian School Certificate Examinations (CISCE / ICSE)'),
            ('STATE', 'State Board of School Education'),
            ('IB', 'International Baccalaureate (IB)'),
            ('CAMBRIDGE', 'Cambridge International (CAIE)')
        ],
        default='CBSE'
    )
    affiliation_number = models.CharField(max_length=100, blank=True, default='2130894')
    school_board_code = models.CharField(max_length=50, blank=True, default='08124')
    trust_society_name = models.CharField(max_length=255, blank=True, default='Horizon Educational & Charitable Trust')
    trust_registration_no = models.CharField(max_length=100, blank=True, default='REG/DEL/2012/9842')
    affiliation_valid_upto = models.DateField(null=True, blank=True)
    rte_quota_seats_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=25.00,
        help_text=_('Right to Education (RTE 25%) mandatory seat quota')
    )

    # --------------------------------------------------------------------------
    # 3. Operating Shifts, Calendar & Bell Schedule
    # --------------------------------------------------------------------------
    operating_shift = models.CharField(
        max_length=50,
        choices=[
            ('SINGLE', 'Single Shift (Morning Standard)'),
            ('DOUBLE_MORNING', 'Double Shift - Morning Wing'),
            ('DOUBLE_AFTERNOON', 'Double Shift - Afternoon Wing')
        ],
        default='SINGLE'
    )
    school_start_time = models.TimeField(default='07:45:00')
    school_end_time = models.TimeField(default='14:15:00')
    assembly_duration_minutes = models.PositiveIntegerField(default=20)
    period_duration_minutes = models.PositiveIntegerField(default=40)
    recess_duration_minutes = models.PositiveIntegerField(default=30)
    working_days_per_week = models.PositiveIntegerField(
        choices=[
            (5, '5-Day Week (Monday to Friday)'),
            (6, '6-Day Week (Mon-Sat with Alternate Saturday Off)')
        ],
        default=6
    )

    # --------------------------------------------------------------------------
    # 4. Omnichannel Communication & Gateways
    # --------------------------------------------------------------------------
    enable_whatsapp_notifications = models.BooleanField(
        default=True,
        help_text=_('Send real-time fee receipts & absent alerts via WhatsApp')
    )
    whatsapp_api_provider = models.CharField(
        max_length=50,
        choices=[
            ('OFFICIAL_CLOUD', 'Official Meta WhatsApp Cloud API'),
            ('TWILIO', 'Twilio WhatsApp Gateway'),
            ('AISENSY', 'AiSensy / Gallabox Indian Partner API')
        ],
        default='OFFICIAL_CLOUD'
    )
    enable_sms_dlt_gateway = models.BooleanField(
        default=True,
        help_text=_('Enable Indian TRAI/DLT compliant SMS gateway')
    )
    sms_sender_id = models.CharField(max_length=10, blank=True, default='HRZNSC')
    enable_email_notifications = models.BooleanField(default=True)

    # --------------------------------------------------------------------------
    # 5. Print Master, Signatures & Watermarks
    # --------------------------------------------------------------------------
    principal_signature = models.ImageField(upload_to='school/signatures/', blank=True, null=True)
    exam_incharge_signature = models.ImageField(upload_to='school/signatures/', blank=True, null=True)
    school_stamp = models.ImageField(upload_to='school/stamps/', blank=True, null=True)
    fee_receipt_format = models.CharField(
        max_length=50,
        choices=[
            ('3_COPY_STRIP', '3-Copy Bank/School/Student Strip (CBSE Standard)'),
            ('A4_DUAL', 'A4 Dual Copy Format'),
            ('THERMAL_POS', '80mm Thermal POS Receipt')
        ],
        default='3_COPY_STRIP'
    )
    report_card_layout = models.CharField(
        max_length=50,
        choices=[
            ('CBSE_2TERM', 'CBSE 2-Term Standard CCE Format'),
            ('NEP_HPC', 'NEP 2020 Holistic Progress Card (HPC)')
        ],
        default='CBSE_2TERM'
    )

    # --------------------------------------------------------------------------
    # 6. Enterprise Security & Audit
    # --------------------------------------------------------------------------
    session_timeout_minutes = models.PositiveIntegerField(
        default=30,
        help_text=_('Idle session timeout before automatic logout')
    )
    enable_staff_2fa = models.BooleanField(
        default=False,
        help_text=_('Require 2FA OTP for Admins and Finance Officers')
    )
    enable_ip_whitelisting = models.BooleanField(
        default=False,
        help_text=_('Restrict POS & sensitive operations to authorized campus IPs')
    )
    whitelisted_ips = models.TextField(
        blank=True,
        default='127.0.0.1, 192.168.1.0/24'
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce singleton pattern (pk=1)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj


class AuditLog(models.Model):
    """
    Immutable audit logging of sensitive administrative, academic, and financial operations.
    """
    class Action(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        LOGIN = 'LOGIN', _('Login')
        LOGOUT = 'LOGOUT', _('Logout')
        FAILED_LOGIN = 'FAILED_LOGIN', _('Failed Login')
        EXPORT = 'EXPORT', _('Data Export')
        BULK_ACTION = 'BULK_ACTION', _('Bulk Action')
        STATUS_CHANGE = 'STATUS_CHANGE', _('Status Change')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    module = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['module', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        user_str = self.user.get_full_name() if self.user else 'System'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.action} on {self.module} ({self.object_repr})"


class SoftwareLicense(models.Model):
    """
    Singleton model recording software trial status, installed commercial license key,
    machine installation identifier, and cryptographic verification metadata.
    """
    license_key = models.TextField(blank=True, help_text=_('Cryptographic license key string issued by developer'))
    license_type = models.CharField(
        max_length=50,
        default='TRIAL',
        choices=[
            ('TRIAL', '7-Day Trial Mode'),
            ('STANDARD', 'Standard Commercial (1-Year)'),
            ('PRO', 'Professional Commercial'),
            ('ENTERPRISE', 'Enterprise Permanent Lifetime'),
            ('EXTENDED_TRIAL', 'Extended Evaluation Trial'),
        ]
    )
    status = models.CharField(
        max_length=50,
        default='TRIAL_ACTIVE',
        choices=[
            ('TRIAL_ACTIVE', '7-Day Trial Active'),
            ('ACTIVE', 'Commercial License Active'),
            ('TRIAL_EXPIRED', '7-Day Trial Expired'),
            ('EXPIRED', 'Commercial License Expired'),
            ('INVALID', 'Invalid / Tampered License'),
            ('REVOKED', 'License Revoked'),
        ]
    )
    trial_start_date = models.DateTimeField(auto_now_add=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    trial_consumed = models.BooleanField(default=False, help_text=_('Prevents trial restart after expiration'))
    valid_until = models.DateField(null=True, blank=True, help_text=_('Null indicates permanent lifetime license'))
    licensed_to_name = models.CharField(max_length=255, blank=True, default='Horizon Public School')
    licensed_to_code = models.CharField(max_length=100, blank=True, default='HPS-DELHI')
    installation_id = models.CharField(max_length=100, unique=True, help_text=_('Unique hardware/installation node identifier'))
    activated_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(auto_now=True)
    last_system_time = models.DateTimeField(null=True, blank=True, help_text=_('Protects against clock rollback tampering'))
    consumed_nonces = models.JSONField(default=list, blank=True, help_text=_('Anti-replay ledger of consumed key nonces'))
    meta_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SoftwareLicense({self.status} - {self.license_type} - {self.installation_id})"

    def save(self, *args, **kwargs):
        # Enforce singleton pattern (pk=1)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_license(cls):
        license_obj, created = cls.objects.get_or_create(pk=1)
        return license_obj


class ConsumedLicenseHistory(models.Model):
    """
    Immutable audit ledger of all cryptographic license tokens ever activated on this system.
    Guarantees anti-replay security: expired or consumed keys cannot be re-used.
    """
    nonce = models.CharField(max_length=64, unique=True, db_index=True)
    plan_type = models.CharField(max_length=50)
    licensed_to_code = models.CharField(max_length=100)
    licensed_to_name = models.CharField(max_length=255)
    issued_date = models.CharField(max_length=30)
    expires_str = models.CharField(max_length=30)
    activated_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    meta_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-activated_at']
        verbose_name = _('Consumed License Token')
        verbose_name_plural = _('Consumed License Tokens')

    def __str__(self):
        return f"Nonce({self.nonce}) - {self.plan_type} - {self.expires_str}"


