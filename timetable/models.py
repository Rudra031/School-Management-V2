import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class TimeSlot(BaseModel):
    """
    Period / Time Slot definition (e.g. Period 1: 08:30 - 09:15).
    """
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='time_slots')
    period_number = models.PositiveSmallIntegerField(help_text=_('Sequential index e.g. 1, 2, 3'))
    name = models.CharField(max_length=50, help_text=_('e.g. Period 1, Recess, Assembly'))
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False, help_text=_('Break or lunch interval'))

    class Meta:
        ordering = ['academic_year', 'period_number']
        unique_together = ('academic_year', 'period_number')
        verbose_name = _('Time Slot')
        verbose_name_plural = _('Time Slots')

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class ClassTimetable(BaseModel):
    """
    Timetable Schedule Entry.
    Prevents section, teacher, and room collision conflicts.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, _('Monday')
        TUESDAY = 2, _('Tuesday')
        WEDNESDAY = 3, _('Wednesday')
        THURSDAY = 4, _('Thursday')
        FRIDAY = 5, _('Friday')
        SATURDAY = 6, _('Saturday')
        SUNDAY = 7, _('Sunday')

    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='timetable_entries')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='timetable_entries')
    day_of_week = models.PositiveSmallIntegerField(choices=DayOfWeek.choices, default=DayOfWeek.MONDAY)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='timetable_entries')
    teacher = models.ForeignKey('staff.StaffMember', on_delete=models.CASCADE, related_name='timetable_entries')
    room_number = models.CharField(max_length=50, blank=True, help_text=_('e.g. Room 204, Lab 1'))

    class Meta:
        ordering = ['day_of_week', 'time_slot__period_number']
        unique_together = (
            # 1. Section cannot have duplicate classes in same period
            ('academic_year', 'section', 'day_of_week', 'time_slot'),
            # 2. Teacher cannot teach two classes in same period
            ('academic_year', 'teacher', 'day_of_week', 'time_slot'),
        )
        verbose_name = _('Timetable Entry')
        verbose_name_plural = _('Timetable Entries')

    def __str__(self):
        return f"{self.section} | {self.get_day_of_week_display()} {self.time_slot.name}: {self.subject.name} ({self.teacher.full_name})"
