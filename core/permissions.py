from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from rest_framework import permissions

def check_user_role(user, allowed_roles):
    """
    Check if user is authenticated, active, and has one of the allowed roles.
    Superusers automatically have access.
    """
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.user_type == 'SUPERADMIN':
        return True
    return user.user_type in allowed_roles


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    CBV mixin that enforces that the user belongs to at least one of the `allowed_roles`.
    """
    allowed_roles = []

    def test_func(self):
        return check_user_role(self.request.user, self.allowed_roles)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Access Denied: You do not have permission to view this resource.")
        raise PermissionDenied("You do not have permission to view this page.")


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN']


class PrincipalRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL']


class SchoolAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN']


class AdminOrPrincipalRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN']


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']


class AcademicStaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']


class AccountantRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT']


class FinancialStaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT']


class LibrarianRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'LIBRARIAN']


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'STUDENT']


class ParentRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PARENT']


class StaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'STAFF']


def role_required(allowed_roles):
    """
    Function-based view decorator enforcing role-based access.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not check_user_role(request.user, allowed_roles):
                if not request.user.is_authenticated:
                    return redirect(f"{settings.LOGIN_URL}?next={request.path}")
                messages.error(request, "Access Denied: You lack permissions for this action.")
                raise PermissionDenied("Access Denied.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Django REST Framework Permissions
class IsRoleAllowedDRF(permissions.BasePermission):
    """
    DRF permission checking allowed roles in `allowed_roles` attribute of the view.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) == 'SUPERADMIN':
            return True
        allowed_roles = getattr(view, 'allowed_roles', [])
        return request.user.user_type in allowed_roles
