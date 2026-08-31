from django import forms
from django.utils.translation import gettext_lazy as _
from academics.models import AcademicYear, Department, ClassLevel, Section, Subject, ClassSubject, SubjectTeacherAllocation
from staff.models import StaffMember

class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current', 'is_closed']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2025-2026'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'head_of_department', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Science & Technology'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SCI'}),
            'head_of_department': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ClassLevelForm(forms.ModelForm):
    class Meta:
        model = ClassLevel
        fields = ['name', 'numeric_level', 'department', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Grade 10'}),
            'numeric_level': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['class_level', 'name', 'room_number', 'class_teacher', 'max_capacity']
        widgets = {
            'class_level': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A, B, Ruby'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Room 204'}),
            'class_teacher': forms.Select(attrs={'class': 'form-select'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'subject_type', 'department', 'credit_hours', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mathematics'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MATH-101'}),
            'subject_type': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'credit_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SubjectTeacherAllocationForm(forms.ModelForm):
    class Meta:
        model = SubjectTeacherAllocation
        fields = ['academic_year', 'section', 'subject', 'teacher']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'section': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
        }
