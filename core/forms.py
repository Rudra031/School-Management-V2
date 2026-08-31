from django import forms
from core.models import SchoolSetting

class SchoolSettingForm(forms.ModelForm):
    class Meta:
        model = SchoolSetting
        fields = '__all__'
        widgets = {
            # Identity & Branding
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            
            # Contact & Location
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': ' '}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            
            # Localization
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'date_format': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'attendance_threshold_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': ' '}),
            
            # Portal Access
            'enable_student_login': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_parent_login': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_online_admissions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

            # Rules & Regulations & Student Discipline
            'discipline_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ' '}),
            'uniform_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ' '}),
            'mobile_device_policy': forms.Select(attrs={'class': 'form-select'}),
            'late_coming_grace_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '60', 'placeholder': ' '}),
            'late_marks_for_half_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10', 'placeholder': ' '}),
            'consecutive_absence_warning_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '30', 'placeholder': ' '}),
            'medical_leave_cert_threshold_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '15', 'placeholder': ' '}),
            'late_fee_per_day': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '0', 'placeholder': ' '}),
            'fee_due_day_of_month': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31', 'placeholder': ' '}),
            'sibling_concession_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0', 'max': '100', 'placeholder': ' '}),
            'passing_marks_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0', 'max': '100', 'placeholder': ' '}),
            'ptm_visiting_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'grievance_escalation_matrix': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': ' '}),

            # Board Affiliation & Legal Master
            'board_name': forms.Select(attrs={'class': 'form-select'}),
            'affiliation_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'school_board_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'trust_society_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'trust_registration_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'affiliation_valid_upto': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'rte_quota_seats_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0', 'max': '100', 'placeholder': ' '}),

            # Shifts & Bell Schedule
            'operating_shift': forms.Select(attrs={'class': 'form-select'}),
            'school_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'school_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'assembly_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '60', 'placeholder': ' '}),
            'period_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'max': '120', 'placeholder': ' '}),
            'recess_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '90', 'placeholder': ' '}),
            'working_days_per_week': forms.Select(attrs={'class': 'form-select'}),

            # Omnichannel Communication
            'enable_whatsapp_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_api_provider': forms.Select(attrs={'class': 'form-select'}),
            'enable_sms_dlt_gateway': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_sender_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'enable_email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

            # Print Master & Signatures
            'fee_receipt_format': forms.Select(attrs={'class': 'form-select'}),
            'report_card_layout': forms.Select(attrs={'class': 'form-select'}),

            # Enterprise Security
            'session_timeout_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '5', 'max': '1440', 'placeholder': ' '}),
            'enable_staff_2fa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_ip_whitelisting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whitelisted_ips': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': ' '}),
        }
