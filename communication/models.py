import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class Notice(BaseModel):
    """
    Campus-wide notice board announcement with persona targeting.
    """
    class Audience(models.TextChoices):
        ALL = 'ALL', _('All School Personas')
        TEACHERS = 'TEACHERS', _('Teachers & Faculty Only')
        STUDENTS = 'STUDENTS', _('Students Only')
        PARENTS = 'PARENTS', _('Parents & Guardians Only')
        STAFF = 'STAFF', _('Non-Teaching Staff Only')

    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    attachment = models.FileField(upload_to='notices/attachments/%Y/%m/', blank=True, null=True)
    is_pinned = models.BooleanField(default=False, help_text=_('Pins notice to the top of notice board'))
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateField(null=True, blank=True, help_text=_('Optional expiration date'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_notices'
    )

    class Meta:
        ordering = ['-is_pinned', '-published_at']
        verbose_name = _('Notice Board Announcement')
        verbose_name_plural = _('Notice Board Announcements')

    def __str__(self):
        return f"{self.title} ({self.get_target_audience_display()})"


class InAppNotification(BaseModel):
    """
    Personalized in-app notification message.
    """
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('In-App Notification')
        verbose_name_plural = _('In-App Notifications')

    def __str__(self):
        return f"{self.recipient.email} - {self.title} ({'Read' if self.is_read else 'Unread'})"
