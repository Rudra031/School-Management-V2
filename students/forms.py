from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from accounts.models import User, UserRole
from students.models import Student, StudentEnrollment, StudentHealthRecord, StudentMedicalIncident
from academics.models import AcademicYear, ClassLevel, Section

class StudentRegistrationForm(forms.ModelForm):
    """
    All-in-one registration form that creates:
    1. User Account (optional login)
    2. Student Master Record
    3. StudentEnrollment (Section + Roll No + Academic Year)
    """
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@school.edu'}),
        help_text=_('Optional: If provided, allows student portal login.')
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        initial='Student@12345'
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_closed=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Enrollment Academic Year')
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_deleted=False).select_related('class_level'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Class & Section')
    )
    roll_number = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        label=_('Roll Number')
    )

    class Meta:
        model = Student
        fields = [
            'admission_number', 'student_id', 'first_name', 'middle_name', 'last_name',
            'gender', 'date_of_birth', 'admission_date', 'blood_group', 'religion',
            'caste_category', 'nationality', 'residential_address', 'city', 'state',
            'postal_code', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'previous_school_name', 'previous_school_tc_number', 'photo'
        ]
        widgets = {
            'admission_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ADM-2026-0001'}),
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. STU-1001'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            'caste_category': forms.TextInput(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Father, Mother'}),
            'previous_school_name': forms.TextInput(attrs={'class': 'form-control'}),
            'previous_school_tc_number': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('academic_year')
        section = cleaned_data.get('section')
        roll = cleaned_data.get('roll_number')

        if year and section and roll:
            # Check for duplicate roll number in the same section and academic year
            if StudentEnrollment.objects.filter(academic_year=year, section=section, roll_number=roll, is_deleted=False).exists():
                self.add_error('roll_number', f"Roll Number {roll} is already assigned in {section} for {year.name}.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        year = self.cleaned_data['academic_year']
        section = self.cleaned_data['section']
        roll = self.cleaned_data['roll_number']

        user = None
        if email:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': self.cleaned_data['first_name'],
                    'last_name': self.cleaned_data['last_name'],
                    'user_type': UserRole.STUDENT,
                }
            )
            if created:
                user.set_password(password or 'Student@12345')
                user.save()

        student = super().save(commit=False)
        student.user = user
        if commit:
            student.save()

            # Create initial StudentEnrollment
            StudentEnrollment.objects.create(
                student=student,
                academic_year=year,
                section=section,
                roll_number=roll,
                enrollment_date=student.admission_date,
                is_current=True
            )
        return student


class StudentUpdateForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth',
            'admission_date', 'blood_group', 'religion', 'caste_category',
            'nationality', 'residential_address', 'permanent_address', 'city',
            'state', 'postal_code', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'status', 'photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            'caste_category': forms.TextInput(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'permanent_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class StudentHealthRecordForm(forms.ModelForm):
    class Meta:
        model = StudentHealthRecord
        fields = [
            'blood_group', 'allergies_summary', 'chronic_conditions',
            'medications', 'dietary_restrictions', 'doctor_name',
            'doctor_phone', 'insurance_policy_number', 'additional_notes'
        ]
        widgets = {
            'blood_group': forms.TextInput(attrs={'class': 'form-control'}),
            'allergies_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List any drug, food, or seasonal allergies...'}),
            'chronic_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Asthma, Diabetes, etc.'}),
            'medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'doctor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'doctor_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StudentMedicalIncidentForm(forms.ModelForm):
    class Meta:
        model = StudentMedicalIncident
        fields = ['incident_date', 'title', 'description', 'treatment_given', 'referred_to_hospital', 'hospital_name']
        widgets = {
            'incident_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sports Sprain in PE Class'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment_given': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'referred_to_hospital': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hospital_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional if referred'}),
        }


class StudentPromotionForm(forms.Form):
    from_academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Current Academic Session')
    )
    from_section = forms.ModelChoiceField(
        queryset=Section.objects.all().select_related('class_level'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Current Class Section')
    )
    to_academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.filter(is_closed=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Promote to Academic Session')
    )
    to_section = forms.ModelChoiceField(
        queryset=Section.objects.all().select_related('class_level'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Promote to Class Section')
    )
