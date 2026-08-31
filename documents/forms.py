from django import forms
from documents.models import DocumentCategory, SchoolDocument, IssuedCertificate, IDCardConfiguration

class SchoolDocumentForm(forms.ModelForm):
    class Meta:
        model = SchoolDocument
        fields = ['title', 'category', 'document_file', 'student', 'staff_member', 'access_level', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document Title...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'document_file': forms.FileInput(attrs={'class': 'form-control'}),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'staff_member': forms.Select(attrs={'class': 'form-select'}),
            'access_level': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TransferCertificateGenerateForm(forms.ModelForm):
    class Meta:
        model = IssuedCertificate
        fields = [
            'student', 'academic_year', 'book_number', 'serial_number',
            'issue_date', 'leaving_date', 'reason_for_leaving', 'general_conduct',
            'dues_cleared', 'total_working_days', 'total_present_days',
            'last_class_passed', 'qualified_for_promotion',
            'ncc_cadet_or_scout', 'games_played', 'custom_remarks'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'book_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. B-01'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 042'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'leaving_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason_for_leaving': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Parents Relocation / Course Completion'}),
            'general_conduct': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Exemplary / Good'}),
            'dues_cleared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'total_working_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_present_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'last_class_passed': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Class 10 (AISSE CBSE)'}),
            'qualified_for_promotion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ncc_cadet_or_scout': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. N/A or Scout Member'}),
            'games_played': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Football School Team Captain'}),
            'custom_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional additional institutional remarks...'}),
        }


class GenericCertificateGenerateForm(forms.ModelForm):
    class Meta:
        model = IssuedCertificate
        fields = [
            'student', 'certificate_type', 'academic_year',
            'issue_date', 'general_conduct', 'dues_cleared',
            'custom_remarks'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'certificate_type': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'general_conduct': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Very Good'}),
            'dues_cleared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Custom certificate certification text...'}),
        }


class IDCardDesignConfigForm(forms.ModelForm):
    class Meta:
        model = IDCardConfiguration
        fields = [
            'name', 'orientation', 'theme', 'primary_color', 'accent_color',
            'show_blood_group', 'show_emergency_contact', 'show_residential_address',
            'show_bus_route', 'show_barcode', 'show_qr_code', 'return_policy_text', 'is_default'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Configuration Name'}),
            'orientation': forms.Select(attrs={'class': 'form-select'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'show_blood_group': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_emergency_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_residential_address': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_bus_route': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_barcode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_qr_code': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'return_policy_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

