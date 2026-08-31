from django import forms
from django.utils.translation import gettext_lazy as _
from assignments.models import Assignment, AssignmentSubmission
from academics.models import AcademicYear, Section, Subject

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['academic_year', 'section', 'subject', 'title', 'description', 'attachment_file', 'assigned_date', 'due_date', 'max_points', 'status']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'section': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Chapter 4 Calculus Problem Set'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment_file': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_points': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_file', 'submission_text']
        widgets = {
            'submission_file': forms.FileInput(attrs={'class': 'form-control'}),
            'submission_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional comments or notes...'}),
        }


class AssignmentGradingForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['score_obtained', 'feedback', 'status']
        widgets = {
            'score_obtained': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
