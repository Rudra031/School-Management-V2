from django import forms
from django.utils import timezone
from leave.models import LeaveType, LeaveRequest

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'attachment']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for leave...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', "End date cannot be earlier than start date.")
        return cleaned_data


class LeaveReviewForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'review_remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Review comments / rationale...'}),
        }
