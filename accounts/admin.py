from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from accounts.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'phone_number', 'is_active', 'is_staff')
    list_filter = ('user_type', 'is_active', 'is_staff', 'gender', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'username')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Information'), {'fields': ('first_name', 'last_name', 'user_type', 'gender', 'date_of_birth', 'avatar')}),
        (_('Contact Details'), {'fields': ('phone_number', 'address')}),
        (_('Permissions & Access'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'must_change_password')}),
        (_('Security & Dates'), {'fields': ('last_login', 'date_joined', 'last_login_ip')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'user_type', 'password1', 'password2'),
        }),
    )
