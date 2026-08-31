from django import forms
from django.utils.translation import gettext_lazy as _
from timetable.models import TimeSlot, ClassTimetable
from academics.models import AcademicYear, Section, Subject
from staff.models import StaffMember

class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['academic_year', 'period_number', 'name', 'start_time', 'end_time', 'is_break']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'period_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Period 1'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_break': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClassTimetableForm(forms.ModelForm):
    class Meta:
        model = ClassTimetable
        fields = ['academic_year', 'section', 'day_of_week', 'time_slot', 'subject', 'teacher', 'room_number']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'section': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'time_slot': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Room 204'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('academic_year')
        sec = cleaned_data.get('section')
        day = cleaned_data.get('day_of_week')
        slot = cleaned_data.get('time_slot')
        teacher = cleaned_data.get('teacher')
        room = cleaned_data.get('room_number')

        if year and day and slot:
            # 1. Check Section Collision
            sec_collision = ClassTimetable.objects.filter(
                academic_year=year, section=sec, day_of_week=day, time_slot=slot, is_deleted=False
            )
            if self.instance.pk:
                sec_collision = sec_collision.exclude(pk=self.instance.pk)
            if sec_collision.exists():
                self.add_error('time_slot', f"{sec} already has a scheduled subject during {slot.name} on this day.")

            # 2. Check Teacher Collision
            if teacher:
                teacher_collision = ClassTimetable.objects.filter(
                    academic_year=year, teacher=teacher, day_of_week=day, time_slot=slot, is_deleted=False
                )
                if self.instance.pk:
                    teacher_collision = teacher_collision.exclude(pk=self.instance.pk)
                if teacher_collision.exists():
                    collided_entry = teacher_collision.first()
                    self.add_error('teacher', f"Teacher {teacher.full_name} is already teaching {collided_entry.section} during {slot.name} on this day.")

            # 3. Check Room Collision
            if room:
                room_collision = ClassTimetable.objects.filter(
                    academic_year=year, room_number__iexact=room, day_of_week=day, time_slot=slot, is_deleted=False
                )
                if self.instance.pk:
                    room_collision = room_collision.exclude(pk=self.instance.pk)
                if room_collision.exists():
                    collided_entry = room_collision.first()
                    self.add_error('room_number', f"Room '{room}' is already booked for {collided_entry.section} during {slot.name}.")

        return cleaned_data
