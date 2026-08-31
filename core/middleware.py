import json
from django.utils.deprecation import MiddlewareMixin
from core.models import AuditLog

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware that captures client IP address and user-agent for logging and session security.
    """
    def process_request(self, request):
        request.client_ip = get_client_ip(request)
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')


class ActiveAcademicYearMiddleware(MiddlewareMixin):
    """
    Middleware that dynamically resolves and attaches the current AcademicYear to request.
    """
    def process_request(self, request):
        request.academic_year = None
        try:
            from academics.models import AcademicYear
            # Find the active academic year
            current_year = AcademicYear.objects.filter(is_current=True, is_closed=False).first()
            if not current_year:
                # Fallback to most recent open year
                current_year = AcademicYear.objects.filter(is_closed=False).order_by('-start_date').first()
            request.academic_year = current_year
        except Exception:
            # During initial migrations or before academics app is migrated
            request.academic_year = None


class SoftwareLicenseMiddleware(MiddlewareMixin):
    """
    Middleware that enforces the 7-day trial period and commercial license activation.
    Redirects locked operations to the activation screen when trial has expired.
    """
    EXEMPT_PREFIXES = (
        '/static/',
        '/media/',
        '/accounts/login/',
        '/accounts/logout/',
        '/core/license/',
        '/core/settings/',
        '/core/backup/',
        '/core/restore/',
        '/core/factory-reset/',
        '/admin/',
    )

    def process_request(self, request):
        request.license_info = None
        try:
            from core import licensing
            license_eval = licensing.evaluate_system_license()
            request.license_info = license_eval

            # If trial is expired or license is invalid, protect internal ERP portal routes
            if license_eval.get('is_expired') or not license_eval.get('is_valid', True):
                path = request.path_info

                # Allow public marketing website (homepage, /portal/*) and exempt endpoints
                is_exempt = any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES)
                is_public_site = path == '/' or path.startswith('/portal/')

                if not is_exempt and not is_public_site:
                    from django.shortcuts import redirect
                    from django.urls import reverse
                    lockout_url = reverse('core:license_lockout')
                    if path != lockout_url:
                        return redirect(lockout_url)
        except Exception:
            # Prevent middleware breakage during initial setup / unmigrated states
            pass

