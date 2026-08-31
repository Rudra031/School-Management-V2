import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class StudentAttendanceSheet(BaseModel):
    """
    Daily attendance register header for a specific Section and Date.
    Prevents duplicate attendance registers via unique constraint.
    """
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='student_attendance_sheets')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='attendance_sheets')
    date = models.DateField(db_index=True)
    taken_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance_sheets'
    )
    is_finalized = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date', 'section']
        unique_together = ('section', 'date')
        verbose_name = _('Student Attendance Sheet')
        verbose_name_plural = _('Student Attendance Sheets')

    def __str__(self):
        return f"{self.section} Attendance ({self.date.strftime('%Y-%m-%d')})"

    @property
    def total_students(self):
        return self.records.count()

    @property
    def present_count(self):
        return self.records.filter(status=StudentAttendanceRecord.Status.PRESENT).count()

    @property
    def absent_count(self):
        return self.records.filter(status=StudentAttendanceRecord.Status.ABSENT).count()


class StudentAttendanceRecord(BaseModel):
    """
    Individual student daily attendance entry.
    """
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Late')
        HALF_DAY = 'HALF_DAY', _('Half Day')
        EXCUSED_LEAVE = 'EXCUSED_LEAVE', _('Excused Leave')

    sheet = models.ForeignKey(StudentAttendanceSheet, on_delete=models.CASCADE, related_name='records')
    student_enrollment = models.ForeignKey('students.StudentEnrollment', on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['student_enrollment__roll_number']
        unique_together = ('sheet', 'student_enrollment')
        verbose_name = _('Student Attendance Record')
        verbose_name_plural = _('Student Attendance Records')

    def __str__(self):
        return f"{self.student_enrollment.student.full_name} - {self.get_status_display()} ({self.sheet.date})"


class StaffAttendanceRecord(BaseModel):
    """
    Staff / Teacher daily attendance log.
    """
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', _('Present')
        ABSENT = 'ABSENT', _('Absent')
        LATE = 'LATE', _('Late')
        ON_LEAVE = 'ON_LEAVE', _('On Approved Leave')

    staff_member = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(db_index=True)
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-date', 'staff_member']
        unique_together = ('staff_member', 'date')
        verbose_name = _('Staff Attendance Record')
        verbose_name_plural = _('Staff Attendance Records')

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.get_status_display()} ({self.date})"
