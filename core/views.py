from io import StringIO
import tempfile
import os
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import UpdateView
from django.contrib import messages
from django.http import HttpResponse
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from core.models import SchoolSetting, AuditLog
from core.forms import SchoolSettingForm
from core.permissions import AdminOrPrincipalRequiredMixin, SuperAdminRequiredMixin
from core.utils import log_audit
from accounts.models import User, UserRole

class SchoolSettingsView(AdminOrPrincipalRequiredMixin, UpdateView):
    model = SchoolSetting
    form_class = SchoolSettingForm
    template_name = 'core/settings.html'
    success_url = reverse_lazy('core:settings')

    def get_object(self, queryset=None):
        return SchoolSetting.get_settings()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_audits'] = AuditLog.objects.filter().order_by('-timestamp')[:8]
        from core import licensing
        context['license_eval'] = licensing.evaluate_system_license()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.UPDATE,
            module='SETTINGS',
            model_name='SchoolSetting',
            object_id=str(self.object.pk),
            object_repr=self.object.name,
            changes={'updated_fields': form.changed_data}
        )
        messages.success(self.request, "Institutional settings updated successfully.")
        return response


class LicenseLockoutView(View):
    """
    Lockout screen presented when 7-day trial has expired or license is invalid.
    Allows Admins and Superadmins to input their developer-issued license key.
    """
    def get(self, request, *args, **kwargs):
        from core import licensing
        license_eval = licensing.evaluate_system_license()

        # If license is actually valid and active, redirect to dashboard
        if license_eval.get('is_active') and not license_eval.get('is_expired'):
            return redirect('accounts:dashboard_router')

        return render(request, 'core/license_lockout.html', {
            'license': license_eval,
            'school': SchoolSetting.get_settings()
        })


class LicenseActivateView(View):
    """
    Validates and activates a submitted license key string with anti-replay ledger checking.
    Accessible to authenticated Admins/Superadmins or from the Lockout screen.
    """
    def post(self, request, *args, **kwargs):
        license_key = request.POST.get('license_key', '').strip()
        from core import licensing
        from core.models import SchoolSetting, AuditLog
        from core.utils import log_audit

        if not license_key:
            messages.error(request, "Please enter a valid license key.")
            return redirect(request.META.get('HTTP_REFERER', 'core:settings'))

        school = SchoolSetting.get_settings()
        success, msg, payload = licensing.activate_license_key(license_key, school, user=request.user)

        if not success:
            messages.error(request, f"License Activation Failed: {msg}")
            return redirect(request.META.get('HTTP_REFERER', 'core:settings'))

        # Log audit trail
        if request.user.is_authenticated:
            log_audit(
                request,
                action=AuditLog.Action.UPDATE,
                module='LICENSE',
                model_name='SoftwareLicense',
                object_id='1',
                object_repr=f"License Activated: {payload.get('plan')} ({payload.get('expires')})",
                changes={'plan': payload.get('plan'), 'expires': payload.get('expires'), 'nonce': payload.get('nonce')}
            )

        messages.success(request, msg)

        # Redirect to Dashboard if unlocked, or back to settings/login
        if request.user.is_authenticated:
            return redirect('accounts:dashboard_router')
        return redirect('accounts:login')



class LicenseStatusAPIView(View):
    """
    JSON API returning current license health and remaining days.
    """
    def get(self, request, *args, **kwargs):
        from core import licensing
        from django.http import JsonResponse
        license_eval = licensing.evaluate_system_license()
        # Strip internal objects before JSON serialization
        license_eval.pop('license_obj', None)
        if license_eval.get('valid_until'):
            license_eval['valid_until'] = str(license_eval['valid_until'])
        return JsonResponse(license_eval)



class SystemBackupDownloadView(SuperAdminRequiredMixin, View):
    """
    Exports a full system database snapshot in JSON format.
    """
    def get(self, request, *args, **kwargs):
        try:
            buf = StringIO()
            # Exclude contenttypes, permissions, and sessions to ensure clean restoration
            call_command(
                'dumpdata',
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                exclude=['contenttypes', 'auth.permission', 'sessions'],
                stdout=buf
            )
            data = buf.getvalue()
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"horizon_sms_backup_{timestamp}.json"
            
            response = HttpResponse(data, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            log_audit(
                request,
                action=AuditLog.Action.EXPORT,
                module='Maintenance',
                model_name='Database',
                object_id='ALL',
                object_repr='Full System Backup Download',
                changes={'filename': filename}
            )
            return response
        except Exception as e:
            messages.error(request, f"Failed to generate backup: {str(e)}")
            return redirect('core:settings')


class SystemRestoreUploadView(SuperAdminRequiredMixin, View):
    """
    Restores the database from an uploaded JSON backup file.
    """
    def post(self, request, *args, **kwargs):
        password = request.POST.get('password', '')
        if not request.user.check_password(password):
            messages.error(request, "Authentication failed: Incorrect administrator password. Data restore aborted.")
            return redirect('core:settings')

        backup_file = request.FILES.get('backup_file')
        if not backup_file:
            messages.error(request, "Please select a valid .json backup file to restore.")
            return redirect('core:settings')

        if not backup_file.name.endswith('.json'):
            messages.error(request, "Invalid file format. Only .json backup archives are supported.")
            return redirect('core:settings')

        tmp_path = None
        try:
            # Write uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='wb') as tmp:
                for chunk in backup_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Execute loaddata
            call_command('loaddata', tmp_path)

            log_audit(
                request,
                action=AuditLog.Action.UPDATE,
                module='Maintenance',
                model_name='Database',
                object_id='ALL',
                object_repr='System Restore from Backup File',
                changes={'source_file': backup_file.name}
            )
            messages.success(request, f"System data successfully restored from '{backup_file.name}'.")
        except Exception as e:
            messages.error(request, f"Database restoration error: {str(e)}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        return redirect('core:settings')


class SystemFactoryResetView(SuperAdminRequiredMixin, View):
    """
    Bulletproof Institutional Hard Factory Reset:
    Permanently erases all operational, academic, financial, student, faculty,
    and examination records across all 18 modules with foreign-key safety.
    Requires strict administrator password authentication and confirmation phrase.
    Safely preserves the active Super Administrator account and re-initializes
    baseline academic year, institutional settings, and website configuration.
    """
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        raw_phrase = request.POST.get('confirm_phrase', '').strip()
        normalized_phrase = raw_phrase.upper().replace(' ', '-').replace('_', '')
        password = request.POST.get('password', '')

        # 1. Flexible Confirmation Phrase Validation
        valid_phrases = ['FACTORY-RESET', 'FACTORYRESET', 'RESET', 'CONFIRM-RESET', 'HARD-RESET']
        if normalized_phrase not in valid_phrases:
            messages.error(
                request,
                f"Factory Reset Aborted: You entered '{raw_phrase}'. Please type 'FACTORY-RESET' to confirm authorization."
            )
            return redirect(reverse_lazy('core:settings') + '?tab=10')

        # 2. Strict Administrator Password Authentication
        if not password or not request.user.check_password(password):
            messages.error(
                request,
                "Authentication Failed: Incorrect administrator password. Factory Reset has been safely aborted."
            )
            return redirect(reverse_lazy('core:settings') + '?tab=10')

        try:
            import shutil
            from datetime import date
            from django.conf import settings
            from django.db import connection
            from academics.models import AcademicYear
            from core.models import SchoolSetting
            from website.models import WebsiteThemeConfig

            vendor = connection.vendor
            all_tables = connection.introspection.table_names()

            # Tables to protect from deletion
            preserved_tables = {
                'django_migrations',
                'django_content_type',
                'auth_permission',
                'auth_group',
                'django_session',
                'core_schoolsetting',
            }

            # 3. Database-Level Safe Table Purge (Disabling Foreign Keys for vendor)
            with connection.cursor() as cursor:
                if vendor == 'sqlite':
                    cursor.execute('PRAGMA foreign_keys = OFF;')
                elif vendor == 'mysql':
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')

                # Delete all operational application tables
                for table in all_tables:
                    if table in preserved_tables:
                        continue

                    if table == 'accounts_user':
                        # Preserve superusers and the currently active user
                        if vendor in ('postgresql', 'postgres'):
                            cursor.execute(
                                "DELETE FROM accounts_user WHERE is_superuser = false AND id != %s;",
                                [request.user.id]
                            )
                        else:
                            cursor.execute(
                                "DELETE FROM accounts_user WHERE is_superuser = 0 AND id != %s;",
                                [request.user.id]
                            )
                        continue

                    # Purge table data
                    try:
                        if vendor in ('postgresql', 'postgres'):
                            cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
                        else:
                            cursor.execute(f'DELETE FROM "{table}";')
                            if vendor == 'sqlite':
                                try:
                                    cursor.execute('DELETE FROM sqlite_sequence WHERE name = %s;', [table])
                                except Exception:
                                    pass
                    except Exception:
                        # Fallback simple delete if truncate/quoted delete needs retry
                        try:
                            cursor.execute(f'DELETE FROM {table};')
                        except Exception:
                            pass

                # Clean up orphaned auth permissions and groups links for non-existent users
                try:
                    if 'accounts_user_groups' in all_tables:
                        cursor.execute(
                            f"DELETE FROM accounts_user_groups WHERE user_id NOT IN (SELECT id FROM accounts_user);"
                        )
                    if 'accounts_user_user_permissions' in all_tables:
                        cursor.execute(
                            f"DELETE FROM accounts_user_user_permissions WHERE user_id NOT IN (SELECT id FROM accounts_user);"
                        )
                except Exception:
                    pass

                if vendor == 'sqlite':
                    cursor.execute('PRAGMA foreign_keys = ON;')
                elif vendor == 'mysql':
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')

            # 4. Media Storage Dynamic Cleanup
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.exists(media_root):
                for item in os.listdir(media_root):
                    item_path = os.path.join(media_root, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            # Remove all sub-files inside media folders like avatars, documents
                            for root_dir, dirs, files in os.walk(item_path):
                                for f in files:
                                    try:
                                        os.remove(os.path.join(root_dir, f))
                                    except Exception:
                                        pass
                    except Exception:
                        pass

            # 5. Provision Pristine Baseline Configuration
            curr_year = date.today().year
            AcademicYear.objects.get_or_create(
                name=f"{curr_year}-{curr_year + 1}",
                defaults={
                    'start_date': date(curr_year, 4, 1),
                    'end_date': date(curr_year + 1, 3, 31),
                    'is_current': True
                }
            )

            # Reset School Settings to clean initial baseline
            setting = SchoolSetting.get_settings()
            setting.name = "Horizon Public School"
            setting.code = "HPS-DELHI"
            setting.tagline = "Affiliated to CBSE, New Delhi (Affiliation No. 2430089)"
            setting.currency_symbol = "₹"
            setting.currency_code = "INR"
            setting.attendance_threshold_percentage = 75.00
            setting.late_coming_grace_minutes = 10
            setting.late_fee_per_day = 20.00
            setting.save()

            # Ensure default active Website Theme exists
            WebsiteThemeConfig.get_active()

            # 6. Immutable Security Audit Trail Log
            log_audit(
                request,
                action=AuditLog.Action.DELETE,
                module='Maintenance',
                model_name='System',
                object_id='ALL',
                object_repr='Institutional Hard Factory Reset',
                changes={
                    'status': 'All operational records, classes, finance, exams, students and faculty accounts wiped.',
                    'authorized_by': request.user.email,
                    'timestamp': timezone.now().isoformat()
                }
            )

            messages.success(
                request,
                "Institutional Hard Factory Reset Completed Successfully! All operational data, records, students, and faculty accounts have been completely wiped. Your Superadmin account remains active and default baseline configurations have been restored."
            )
        except Exception as e:
            messages.error(request, f"Factory reset encountered an error: {str(e)}")

        return redirect(reverse_lazy('core:settings') + '?tab=10')


