from django import forms
from django.utils import timezone
from academics.models import Section
from attendance.models import StudentAttendanceRecord, StaffAttendanceRecord

class AttendanceFilterForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_deleted=False).select_related('class_level'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Class & Section'
    )
    date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Attendance Date'
    )


class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendanceRecord
        fields = ['staff_member', 'date', 'check_in_time', 'check_out_time', 'status', 'remarks']
        widgets = {
            'staff_member': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }
