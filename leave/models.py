import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class LeaveType(BaseModel):
    """
    Leave categorization (e.g. Sick Leave, Casual Leave, Annual Leave, Study Leave).
    """
    name = models.CharField(max_length=50, unique=True)
    allocated_days_per_year = models.PositiveSmallIntegerField(default=12)
    is_paid_leave = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Leave Type')
        verbose_name_plural = _('Leave Types')

    def __str__(self):
        return f"{self.name} ({self.allocated_days_per_year} Days/Yr)"


class LeaveRequest(BaseModel):
    """
    Staff / Student leave application record.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Approval')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        CANCELLED = 'CANCELLED', _('Cancelled')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    attachment = models.FileField(upload_to='leaves/attachments/%Y/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_requests'
    )
    review_remarks = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name = _('Leave Request')
        verbose_name_plural = _('Leave Requests')

    def __str__(self):
        return f"{self.user.email} - {self.leave_type.name} ({self.start_date} to {self.end_date}): {self.get_status_display()}"

    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1
