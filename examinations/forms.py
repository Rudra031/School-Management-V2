from django import forms
from django.utils.translation import gettext_lazy as _
from examinations.models import GradeScale, ExamTerm, ExamSchedule

class GradeScaleForm(forms.ModelForm):
    class Meta:
        model = GradeScale
        fields = ['name', 'grade_letter', 'min_percentage', 'max_percentage', 'grade_point', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_letter': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A+'}),
            'min_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grade_point': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ExamTermForm(forms.ModelForm):
    class Meta:
        model = ExamTerm
        fields = ['academic_year', 'title', 'term_type', 'start_date', 'end_date', 'pass_percentage_threshold', 'requires_fee_clearance', 'admit_card_published', 'is_published']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Term 1 Half-Yearly Examinations 2026-27'}),
            'term_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pass_percentage_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'requires_fee_clearance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'admit_card_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExamScheduleForm(forms.ModelForm):
    class Meta:
        model = ExamSchedule
        fields = [
            'exam_term', 'class_level', 'subject', 'exam_date', 'start_time',
            'duration_minutes', 'room_number', 'exam_center', 'max_marks', 'pass_marks',
            'theory_marks_max', 'practical_marks_max', 'internal_marks_max', 'instructions'
        ]
        widgets = {
            'exam_term': forms.Select(attrs={'class': 'form-select'}),
            'class_level': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Examination Hall A-1'}),
            'exam_center': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Senior Wing Campus'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'theory_marks_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'practical_marks_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'internal_marks_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

