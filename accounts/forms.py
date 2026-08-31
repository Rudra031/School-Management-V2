from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from accounts.models import User, UserRole
from students.models import Student
from parents.models import ParentProfile, ParentStudent

class UserLoginForm(forms.Form):
    login_id = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'Enter User ID or Email',
            'autocomplete': 'username',
            'autofocus': True,
            'id': 'id_email' # for backwards compatibility with JS helpers
        }),
        label=_('User ID or Email Address')
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'field-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'id_password'
        }),
        label=_('Password')
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Remember me on this device')
    )

    def clean(self):
        cleaned_data = super().clean()
        login_id = cleaned_data.get('login_id')
        password = cleaned_data.get('password')

        if login_id and password:
            self.user = authenticate(login_id=login_id, password=password)
            if self.user is None:
                # Also try standard username/email kwarg
                self.user = authenticate(username=login_id, password=password)
            if self.user is None:
                raise forms.ValidationError(_('Invalid User ID / Email or Password. Please verify and try again.'))
            if not self.user.is_active:
                raise forms.ValidationError(_('This account is currently deactivated. Please contact your school administrator.'))
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'gender', 'date_of_birth', 'address', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ' '}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': ' '})


class ManualUserCreationForm(forms.ModelForm):
    """
    Administrator manual user creation form with explicit User ID, Password assignment,
    and dynamic parent-child linking.
    """
    username = forms.CharField(
        label=_('User ID / Username'),
        max_length=150,
        required=True,
        help_text=_('Unique User ID (e.g. ADM001, TCH_MATH, STU2026_05, PAR001)'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '})
    )
    password = forms.CharField(
        label=_('Initial Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ' '}),
        required=True,
        min_length=8,
        help_text=_('Assign a secure password (minimum 8 characters)')
    )
    confirm_password = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ' '}),
        required=True,
        min_length=8
    )

    # Parent Linking Fields
    linked_children = forms.ModelMultipleChoiceField(
        queryset=Student.objects.filter(is_deleted=False, status=Student.Status.ACTIVE).order_by('first_name', 'last_name'),
        required=False,
        label=_('Select Linked Children / Students'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'})
    )
    relationship_type = forms.ChoiceField(
        choices=ParentStudent.RelationshipType.choices,
        required=False,
        initial=ParentStudent.RelationshipType.FATHER,
        label=_('Relationship to Children'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_primary_contact = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Designate as Primary Contact for SMS & Billing'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_pickup_child = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Authorized for Campus Student Pickup'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'user_type', 'phone_number', 'gender', 'address',
            'is_active', 'must_change_password'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'user_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_user_type'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': ' '}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'must_change_password': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_('A user with this User ID / Username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('A user with this email address already exists.'))
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', _('Passwords do not match. Please verify and re-enter.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            
            # If creating a parent role, automatically configure ParentProfile and ParentStudent links
            if user.user_type == UserRole.PARENT:
                parent_profile, _ = ParentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'primary_phone': user.phone_number or '',
                        'email': user.email,
                        'residential_address': user.address or 'Campus Residential Area'
                    }
                )
                children = self.cleaned_data.get('linked_children')
                if children:
                    rel_type = self.cleaned_data.get('relationship_type') or ParentStudent.RelationshipType.FATHER
                    is_primary = self.cleaned_data.get('is_primary_contact', True)
                    can_pickup = self.cleaned_data.get('can_pickup_child', True)
                    for student in children:
                        ParentStudent.objects.get_or_create(
                            parent=parent_profile,
                            student=student,
                            defaults={
                                'relationship_type': rel_type,
                                'is_primary_contact': is_primary,
                                'can_pickup_child': can_pickup
                            }
                        )
        return user


class ManualUserUpdateForm(forms.ModelForm):
    """
    Administrator user update form for editing user profile, roles, and child relations.
    """
    username = forms.CharField(
        label=_('User ID / Username'),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '})
    )

    # Parent Linking Fields
    linked_children = forms.ModelMultipleChoiceField(
        queryset=Student.objects.filter(is_deleted=False, status=Student.Status.ACTIVE).order_by('first_name', 'last_name'),
        required=False,
        label=_('Linked Children / Students'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'})
    )
    relationship_type = forms.ChoiceField(
        choices=ParentStudent.RelationshipType.choices,
        required=False,
        initial=ParentStudent.RelationshipType.FATHER,
        label=_('Relationship to Children'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_primary_contact = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Designate as Primary Contact for SMS & Billing'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_pickup_child = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Authorized for Campus Student Pickup'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'user_type', 'phone_number', 'gender', 'address',
            'is_active', 'must_change_password'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'user_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_user_type'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': ' '}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'must_change_password': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, 'parent_profile'):
            pp = self.instance.parent_profile
            linked_ids = pp.linked_students.values_list('student_id', flat=True)
            self.fields['linked_children'].initial = Student.objects.filter(id__in=linked_ids)
            first_rel = pp.linked_students.first()
            if first_rel:
                self.fields['relationship_type'].initial = first_rel.relationship_type
                self.fields['is_primary_contact'].initial = first_rel.is_primary_contact
                self.fields['can_pickup_child'].initial = first_rel.can_pickup_child

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A user with this User ID / Username already exists.'))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A user with this email address already exists.'))
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and user.user_type == UserRole.PARENT:
            parent_profile, _ = ParentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'primary_phone': user.phone_number or '',
                    'email': user.email,
                    'residential_address': user.address or 'Campus Residential Area'
                }
            )
            parent_profile.first_name = user.first_name
            parent_profile.last_name = user.last_name
            parent_profile.primary_phone = user.phone_number or ''
            parent_profile.email = user.email
            if user.address:
                parent_profile.residential_address = user.address
            parent_profile.save()

            if 'linked_children' in self.cleaned_data:
                children = self.cleaned_data.get('linked_children') or []
                rel_type = self.cleaned_data.get('relationship_type') or ParentStudent.RelationshipType.FATHER
                is_primary = self.cleaned_data.get('is_primary_contact', True)
                can_pickup = self.cleaned_data.get('can_pickup_child', True)

                # Sync relations
                current_student_ids = [c.id for c in children]
                ParentStudent.objects.filter(parent=parent_profile).exclude(student_id__in=current_student_ids).delete()
                for student in children:
                    ps, created = ParentStudent.objects.get_or_create(
                        parent=parent_profile,
                        student=student,
                        defaults={
                            'relationship_type': rel_type,
                            'is_primary_contact': is_primary,
                            'can_pickup_child': can_pickup
                        }
                    )
                    if not created:
                        ps.relationship_type = rel_type
                        ps.is_primary_contact = is_primary
                        ps.can_pickup_child = can_pickup
                        ps.save()
        return user


class AdminPasswordResetForm(forms.Form):
    """
    Form for Administrator to manually re-assign or reset a user's password.
    """
    new_password = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ' '}),
        required=True,
        min_length=8,
        help_text=_('Enter new password (minimum 8 characters)')
    )
    confirm_password = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': ' '}),
        required=True,
        min_length=8
    )
    must_change_password = forms.BooleanField(
        label=_('Require user to change password on next login'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', _('Passwords do not match.'))
        return cleaned_data
