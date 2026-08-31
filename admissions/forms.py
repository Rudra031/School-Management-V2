from django import forms
from django.utils.translation import gettext_lazy as _
from admissions.models import AdmissionsApplication
from academics.models import AcademicYear, ClassLevel, Section

class PublicAdmissionApplicationForm(forms.ModelForm):
    """
    Public-facing Online Student Admission Application Form.
    Designed for prospective parents applying via the public school portal.
    """
    parent_declaration = forms.BooleanField(
        required=True,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('I hereby declare that all information provided is accurate and authentic to the best of my knowledge.')
    )

    class Meta:
        model = AdmissionsApplication
        fields = [
            'academic_year', 'applying_for_class',
            'first_name', 'middle_name', 'last_name',
            'gender', 'date_of_birth', 'blood_group', 'caste_category', 'aadhaar_number', 'photo',
            'parent_name', 'parent_phone', 'parent_email',
            'father_name', 'father_phone', 'father_occupation',
            'mother_name', 'mother_phone', 'mother_occupation',
            'residential_address', 'city', 'state', 'pin_code',
            'stream_preference', 'previous_school', 'previous_board', 'previous_percentage', 'tc_status',
            'has_sibling_in_school', 'sibling_details'
        ]
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'applying_for_class': forms.Select(attrs={'class': 'form-select', 'required': True, 'id': 'id_applying_for_class'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aarav', 'required': True}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Name (Optional)'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sharma', 'required': True}),
            'gender': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True, 'id': 'id_date_of_birth'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'caste_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'General / OBC / SC / ST / EWS'}),
            'aadhaar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12-digit Aadhaar / National ID No.'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),

            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary Contact Name', 'required': True}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98300 00000', 'required': True}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@example.com', 'required': True}),

            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Father's Full Name"}),
            'father_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Father's Mobile Number"}),
            'father_occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. Software Architect / Doctor / Business"}),

            'mother_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mother's Full Name"}),
            'mother_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mother's Mobile Number"}),
            'mother_occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. Professor / Designer / Homemaker"}),

            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Flat/House No, Building, Street, Landmark...', 'required': True}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'value': 'Kolkata'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State', 'value': 'West Bengal'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PIN Code'}),

            'stream_preference': forms.Select(attrs={'class': 'form-select', 'id': 'id_stream_preference'}),
            'previous_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of last school attended'}),
            'previous_board': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CBSE / ICSE / State Board / IB'}),
            'previous_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 92.50', 'step': '0.01'}),
            'tc_status': forms.Select(attrs={'class': 'form-select'}),

            'has_sibling_in_school': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_sibling_in_school'}),
            'sibling_details': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sibling Name, Admission No., Current Class', 'id': 'id_sibling_details'}),
        }


class AdmissionsApplicationForm(forms.ModelForm):
    class Meta:
        model = AdmissionsApplication
        fields = [
            'academic_year', 'applying_for_class', 'first_name', 'last_name',
            'gender', 'date_of_birth', 'parent_name', 'parent_phone',
            'parent_email', 'residential_address', 'previous_school'
        ]
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'applying_for_class': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aarav'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sharma'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Guardian Name'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-555-0192'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@example.com'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Street, City, Zip Code'}),
            'previous_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional previous school name'}),
        }


class QuickAdmissionForm(forms.ModelForm):
    """
    Mode 1: Rapid 1-Page Student Admission Form.
    """
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_deleted=False),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Assign Section')
    )
    previous_class = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Grade 8'}),
        label=_('Previous Grade/Class')
    )
    admission_type = forms.ChoiceField(
        choices=[('REGULAR', 'Regular Day Scholar'), ('TRANSFER', 'Transfer In'), ('SCHOLARSHIP', 'Merit Scholarship')],
        initial='REGULAR',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Admission Type')
    )


    class Meta:
        model = AdmissionsApplication
        fields = [
            'academic_year', 'applying_for_class', 'first_name', 'last_name',
            'gender', 'date_of_birth', 'parent_name', 'parent_phone',
            'parent_email', 'residential_address', 'previous_school'
        ]
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'applying_for_class': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Last Name'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Father / Guardian Name'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-555-0192'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@domain.com'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Residential Address...'}),
            'previous_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Previous School Name'}),
        }


class AdmissionsReviewForm(forms.ModelForm):
    class Meta:
        model = AdmissionsApplication
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Evaluation / Verification Notes...'}),
        }


class AdmissionsConvertStudentForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_deleted=False),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Assign Section'
    )
    roll_number = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Assign Roll Number'
    )
    admission_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Admission Number'
    )
    student_id = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Student ID'
    )
