from core.models import SchoolSetting

def school_settings(request):
    """
    Exposes global school branding, currency, format, and contact settings to all templates.
    """
    try:
        settings_obj = SchoolSetting.get_settings()
    except Exception:
        settings_obj = None
    return {'school': settings_obj}


def active_academic_year(request):
    """
    Exposes the active academic year to all templates.
    """
    return {'active_academic_year': getattr(request, 'academic_year', None)}


def unread_notifications(request):
    """
    Exposes unread notification count for the authenticated user.
    """
    if request.user.is_authenticated:
        try:
            from communication.models import InAppNotification
            unread_count = InAppNotification.objects.filter(recipient=request.user, is_read=False).count()
            recent_notifs = InAppNotification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
            return {
                'unread_notifications_count': unread_count,
                'recent_notifications': recent_notifs
            }
        except Exception:
            return {'unread_notifications_count': 0, 'recent_notifications': []}
    return {'unread_notifications_count': 0, 'recent_notifications': []}


def just_logged_in_splash(request):
    """
    Exposes and auto-consumes the one-time login splash screen trigger flag.
    """
    show_splash = False
    if hasattr(request, 'session') and request.session.get('just_logged_in'):
        show_splash = True
        try:
            del request.session['just_logged_in']
            request.session.modified = True
        except KeyError:
            pass
    return {'show_login_splash': show_splash}


def license_info(request):
    """
    Exposes software trial status, commercial validity, and remaining days to all templates.
    """
    if hasattr(request, 'license_info') and request.license_info:
        return {'system_license': request.license_info}

    try:
        from core import licensing
        info = licensing.evaluate_system_license()
        return {'system_license': info}
    except Exception:
        return {'system_license': None}


