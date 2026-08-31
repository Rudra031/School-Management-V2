from django import forms
from django.utils.translation import gettext_lazy as _
from accounts.models import User, UserRole
from parents.models import ParentProfile, ParentStudent
from students.models import Student

class ParentProfileCreateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@example.com'}),
        label=_('Email Address / Login ID')
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        initial='Parent@12345',
        help_text=_('Default initial password: Parent@12345')
    )

    class Meta:
        model = ParentProfile
        fields = [
            'first_name', 'last_name', 'father_name', 'mother_name',
            'occupation', 'annual_income', 'primary_phone', 'secondary_phone',
            'residential_address'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'primary_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'residential_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def save(self, commit=True):
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': self.cleaned_data['first_name'],
                'last_name': self.cleaned_data['last_name'],
                'user_type': UserRole.PARENT,
                'phone_number': self.cleaned_data['primary_phone'],
            }
        )
        if created:
            user.set_password(password)
            user.save()

        parent = super().save(commit=False)
        parent.user = user
        if commit:
            parent.save()
        return parent


class StudentModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.full_name} — {obj.admission_number} ({obj.current_class_section})"


class ParentStudentLinkForm(forms.ModelForm):
    student = StudentModelChoiceField(
        queryset=Student.objects.filter(is_deleted=False).order_by('first_name', 'last_name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_student_select'}),
        label=_('Select Student'),
        empty_label=_('-- Choose a Student from Directory --')
    )

    class Meta:
        model = ParentStudent
        fields = ['student', 'relationship_type', 'is_primary_contact', 'can_pickup_child']
        widgets = {
            'relationship_type': forms.Select(attrs={'class': 'form-select'}),
            'is_primary_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_pickup_child': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
