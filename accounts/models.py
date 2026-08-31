from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserRole(models.TextChoices):
    SUPERADMIN = 'SUPERADMIN', _('Super Administrator')
    PRINCIPAL = 'PRINCIPAL', _('Principal')
    ADMIN = 'ADMIN', _('School Administrator')
    TEACHER = 'TEACHER', _('Teacher')
    ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
    LIBRARIAN = 'LIBRARIAN', _('Librarian')
    STUDENT = 'STUDENT', _('Student')
    PARENT = 'PARENT', _('Parent / Guardian')
    STAFF = 'STAFF', _('Support Staff')


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('An email address is required.'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', UserRole.SUPERADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model implementing Role-Based Access Control (RBAC) across 9 personas.
    Email is used as the primary login identifier.
    """
    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    user_type = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True,
        verbose_name=_('Role / User Type')
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    must_change_password = models.BooleanField(
        default=False,
        help_text=_('Forces the user to change their password on the next login.')
    )
    is_verified = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        ordering = ['-date_joined']
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['user_type', 'is_active']),
            models.Index(fields=['email', 'user_type']),
        ]

    def __str__(self):
        name = self.get_full_name()
        return f"{name} ({self.get_user_type_display()})" if name else f"{self.email} ({self.get_user_type_display()})"

    def save(self, *args, **kwargs):
        # Synchronize is_staff flag for administrative roles
        if self.user_type in [UserRole.SUPERADMIN, UserRole.PRINCIPAL, UserRole.ADMIN]:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_superadmin(self):
        return self.user_type == UserRole.SUPERADMIN or self.is_superuser

    @property
    def is_principal(self):
        return self.user_type == UserRole.PRINCIPAL

    @property
    def is_school_admin(self):
        return self.user_type == UserRole.ADMIN

    @property
    def is_teacher(self):
        return self.user_type == UserRole.TEACHER

    @property
    def is_accountant(self):
        return self.user_type == UserRole.ACCOUNTANT

    @property
    def is_librarian(self):
        return self.user_type == UserRole.LIBRARIAN

    @property
    def is_student(self):
        return self.user_type == UserRole.STUDENT

    @property
    def is_parent(self):
        return self.user_type == UserRole.PARENT

    @property
    def is_support_staff(self):
        return self.user_type == UserRole.STAFF

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email.split('@')[0].capitalize()

    @property
    def role_badge_class(self):
        badge_map = {
            UserRole.SUPERADMIN: 'badge-danger',
            UserRole.PRINCIPAL: 'badge-primary',
            UserRole.ADMIN: 'badge-info',
            UserRole.TEACHER: 'badge-success',
            UserRole.ACCOUNTANT: 'badge-warning',
            UserRole.LIBRARIAN: 'badge-secondary',
            UserRole.STUDENT: 'badge-primary-subtle',
            UserRole.PARENT: 'badge-teal',
            UserRole.STAFF: 'badge-dark',
        }
        return badge_map.get(self.user_type, 'badge-secondary')
