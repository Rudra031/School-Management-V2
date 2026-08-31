from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import SchoolSetting, AuditLog
from core.utils import log_audit, export_to_csv, export_to_excel
from accounts.models import UserRole

User = get_user_model()

class CoreModelsAndUtilsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()
        self.password = 'TestPassword123!'
        
        self.superadmin = User.objects.create_superuser(
            email='admin@school.edu',
            password=self.password,
            first_name='Super',
            last_name='Admin'
        )
        self.student = User.objects.create_user(
            email='student@school.edu',
            password=self.password,
            first_name='Test',
            last_name='Student',
            user_type=UserRole.STUDENT
        )

    def test_school_settings_singleton(self):
        """Verify SchoolSetting behaves as a singleton with id=1"""
        setting1 = SchoolSetting.get_settings()
        setting1.name = "Apex Global Academy"
        setting1.save()

        setting2 = SchoolSetting.get_settings()
        self.assertEqual(setting2.name, "Apex Global Academy")
        self.assertEqual(SchoolSetting.objects.count(), 1)

    def test_audit_logging(self):
        """Verify log_audit creates AuditLog records accurately"""
        request = self.factory.get('/')
        request.user = self.superadmin
        request.client_ip = '127.0.0.1'
        request.user_agent = 'Mozilla/5.0 TestBrowser'

        log_audit(
            request,
            action=AuditLog.Action.CREATE,
            module='TestModule',
            model_name='TestModel',
            object_id='101',
            object_repr='Test Object Representation',
            changes={'status': 'Active'}
        )

        log = AuditLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.superadmin)
        self.assertEqual(log.action, AuditLog.Action.CREATE)
        self.assertEqual(log.module, 'TestModule')
        self.assertEqual(log.object_id, '101')
        self.assertEqual(log.changes, {'status': 'Active'})

    def test_csv_export(self):
        """Verify CSV export utility returns valid attachment"""
        headers = ['ID', 'Name', 'Role']
        rows = [['1', 'Alice', 'Student'], ['2', 'Bob', 'Teacher']]
        response = export_to_csv('test_export', headers, rows)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="test_export_', response['Content-Disposition'])

    def test_excel_export(self):
        """Verify Excel XLSX export utility returns valid file response"""
        headers = ['ID', 'Name', 'Role']
        rows = [['1', 'Alice', 'Student'], ['2', 'Bob', 'Teacher']]
        response = export_to_excel('test_excel', 'TestSheet', headers, rows)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'] in [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/csv'
            ]
        )

    def test_school_settings_view_get(self):
        """Verify SuperAdmin can view School Settings page"""
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School Settings &amp; Governance Center")
        self.assertContains(response, "Rules &amp; Regulations")
        self.assertContains(response, "Institutional Identity")

    def test_school_settings_view_permission_denied_for_student(self):
        """Verify Students are denied (403) from accessing Settings"""
        self.client.login(email='student@school.edu', password=self.password)
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 403)

    def test_school_settings_view_post_updates_singleton_and_audits(self):
        """Verify SuperAdmin can update school settings with rules and that an AuditLog entry is recorded"""
        self.client.login(email='admin@school.edu', password=self.password)
        post_data = {
            'name': 'Horizon Premier Public School',
            'code': 'HORIZON-2026',
            'tagline': 'Affiliated to CBSE, New Delhi',
            'address': 'Sector 14, Rohini',
            'city': 'New Delhi',
            'state': 'Delhi',
            'postal_code': '110085',
            'country': 'India',
            'phone': '+91 98765 43210',
            'email': 'contact@horizonacademy.edu.in',
            'website': 'https://horizonacademy.edu.in',
            'currency_symbol': '₹',
            'currency_code': 'INR',
            'date_format': 'd M Y',
            'timezone': 'Asia/Kolkata',
            'attendance_threshold_percentage': '75.00',
            'enable_student_login': 'on',
            'enable_parent_login': 'on',
            'enable_online_admissions': 'on',
            # Rules & Regulations
            'discipline_policy': 'Zero tolerance for bullying. High discipline standards.',
            'uniform_policy': 'Navy blue blazer with school crest.',
            'mobile_device_policy': 'LOCKER_DEPOSITED',
            'late_coming_grace_minutes': 15,
            'late_marks_for_half_day': 3,
            'consecutive_absence_warning_days': 3,
            'medical_leave_cert_threshold_days': 3,
            'late_fee_per_day': '25.00',
            'fee_due_day_of_month': 10,
            'sibling_concession_percentage': '20.00',
            'passing_marks_percentage': '33.00',
            'ptm_visiting_hours': '2nd Saturday 10:00 AM - 01:00 PM',
            'grievance_escalation_matrix': 'Level 1: Class Teacher -> Level 2: Principal',
            # Affiliation
            'board_name': 'CBSE',
            'affiliation_number': '2130894',
            'school_board_code': '08124',
            'trust_society_name': 'Horizon Educational Society',
            'trust_registration_no': 'REG-2012',
            'rte_quota_seats_percentage': '25.00',
            # Shifts
            'operating_shift': 'SINGLE',
            'school_start_time': '08:00:00',
            'school_end_time': '14:00:00',
            'assembly_duration_minutes': 20,
            'period_duration_minutes': 40,
            'recess_duration_minutes': 30,
            'working_days_per_week': 6,
            # Communication
            'enable_whatsapp_notifications': 'on',
            'whatsapp_api_provider': 'OFFICIAL_CLOUD',
            'enable_sms_dlt_gateway': 'on',
            'sms_sender_id': 'HRZNSC',
            'enable_email_notifications': 'on',
            # Print
            'fee_receipt_format': '3_COPY_STRIP',
            'report_card_layout': 'CBSE_2TERM',
            # Security
            'session_timeout_minutes': 30,
            'whitelisted_ips': '127.0.0.1',
        }
        response = self.client.post(reverse('core:settings'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify singleton was updated
        settings_obj = SchoolSetting.get_settings()
        self.assertEqual(settings_obj.name, 'Horizon Premier Public School')
        self.assertEqual(settings_obj.code, 'HORIZON-2026')
        self.assertEqual(settings_obj.late_coming_grace_minutes, 15)
        self.assertEqual(float(settings_obj.late_fee_per_day), 25.0)
        self.assertEqual(settings_obj.board_name, 'CBSE')

        # Verify audit log was created
        audit = AuditLog.objects.filter(module='SETTINGS', model_name='SchoolSetting').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, AuditLog.Action.UPDATE)

    def test_factory_reset_unauthorized_user_denied(self):
        """Verify non-superadmin users are denied from executing factory reset"""
        self.client.login(email='student@school.edu', password=self.password)
        response = self.client.post(
            reverse('core:factory_reset'),
            {'confirm_phrase': 'FACTORY-RESET', 'password': self.password}
        )
        self.assertEqual(response.status_code, 403)

    def test_factory_reset_invalid_phrase_aborts(self):
        """Verify factory reset is aborted if confirmation phrase is incorrect"""
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(
            reverse('core:factory_reset'),
            {'confirm_phrase': 'WRONG-PHRASE', 'password': self.password},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please type &#x27;FACTORY-RESET&#x27;")

    def test_factory_reset_wrong_password_aborts(self):
        """Verify factory reset is aborted if administrator password authentication fails"""
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(
            reverse('core:factory_reset'),
            {'confirm_phrase': 'FACTORY-RESET', 'password': 'WrongAdminPassword123!'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authentication Failed: Incorrect administrator password")

    def test_factory_reset_success_wipes_records_and_restores_baseline(self):
        """Verify authenticated factory reset completely purges operational data and preserves superadmin"""
        # Create some operational data
        from academics.models import ClassLevel, Section
        cl = ClassLevel.objects.create(name="Grade 10", numeric_level=10)
        sec = Section.objects.create(class_level=cl, name="A")
        
        self.assertEqual(User.objects.count(), 2) # superadmin and student
        self.assertEqual(ClassLevel.objects.count(), 1)
        self.assertEqual(Section.objects.count(), 1)

        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(
            reverse('core:factory_reset'),
            {'confirm_phrase': 'FACTORY-RESET', 'password': self.password},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Institutional Hard Factory Reset Completed Successfully")

        # Operational records wiped
        self.assertEqual(ClassLevel.objects.count(), 0)
        self.assertEqual(Section.objects.count(), 0)

        # Superadmin preserved, regular student user removed
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)
        self.assertTrue(User.objects.filter(email='admin@school.edu').exists())
        self.assertFalse(User.objects.filter(email='student@school.edu').exists())

        # Baseline AcademicYear and settings restored
        from academics.models import AcademicYear
        self.assertEqual(AcademicYear.objects.count(), 1)
        self.assertTrue(AcademicYear.objects.filter(is_current=True).exists())

        # AuditLog recorded
        audit = AuditLog.objects.filter(object_repr='Institutional Hard Factory Reset').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, AuditLog.Action.DELETE)


class SoftwareLicensingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'TestPassword123!'
        self.superadmin = User.objects.create_superuser(
            email='admin@horizon.edu',
            password=self.password,
            first_name='Super',
            last_name='Admin'
        )
        self.school = SchoolSetting.get_settings()
        self.school.code = 'HPS-DELHI'
        self.school.name = 'Horizon Public School'
        self.school.save()

    def test_trial_initialization(self):
        """Verify new installation gets 7 days trial access"""
        from core import licensing
        license_eval = licensing.evaluate_system_license()
        self.assertTrue(license_eval['is_valid'])
        self.assertTrue(license_eval['is_trial'])
        self.assertFalse(license_eval['is_expired'])
        self.assertEqual(license_eval['days_remaining'], 7)
        self.assertIn('HPS-DELHI', license_eval['school_code'])

    def test_license_generation_and_verification(self):
        """Verify developer generated license key verifies cryptographically"""
        from core import licensing
        payload = licensing.create_license_payload(
            school_code='HPS-DELHI',
            school_name='Horizon Public School',
            plan_type='STANDARD',
            days=365
        )
        key = licensing.sign_license_payload(payload)
        self.assertTrue(key.startswith('HRZN.'))

        is_valid, status, msg, verified_payload = licensing.verify_license_key(key, current_school_code='HPS-DELHI')
        self.assertTrue(is_valid)
        self.assertEqual(status, licensing.STATUS_ACTIVE)
        self.assertEqual(verified_payload['plan'], 'STANDARD')

    def test_tampered_license_key_rejected(self):
        """Verify forged or modified keys fail HMAC validation"""
        from core import licensing
        payload = licensing.create_license_payload(school_code='HPS-DELHI', days=365)
        key = licensing.sign_license_payload(payload)

        # Tamper the signature or body
        tampered_key = key[:-4] + 'XXXX'
        is_valid, status, msg, _ = licensing.verify_license_key(tampered_key, current_school_code='HPS-DELHI')
        self.assertFalse(is_valid)
        self.assertEqual(status, licensing.STATUS_INVALID)

    def test_wrong_school_code_rejected(self):
        """Verify license key issued for another school cannot be used"""
        from core import licensing
        payload = licensing.create_license_payload(school_code='OTHER-SCHOOL', days=365)
        key = licensing.sign_license_payload(payload)

        is_valid, status, msg, _ = licensing.verify_license_key(key, current_school_code='HPS-DELHI')
        self.assertFalse(is_valid)
        self.assertIn("License was issued for 'OTHER-SCHOOL'", msg)

    def test_expired_trial_middleware_redirect(self):
        """Verify expired trial redirects protected views to lockout screen"""
        from core.models import SoftwareLicense
        from django.utils import timezone
        import datetime

        license_obj = SoftwareLicense.get_license()
        license_obj.installation_id = 'INST-TEST-1234'
        license_obj.trial_start_date = timezone.now() - datetime.timedelta(days=10)
        license_obj.trial_end_date = timezone.now() - datetime.timedelta(days=3)
        license_obj.status = 'TRIAL_EXPIRED'
        license_obj.license_key = ''
        license_obj.save()

        self.client.login(email='admin@horizon.edu', password=self.password)
        # Attempt to access dashboard
        response = self.client.get(reverse('accounts:dashboard_router'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('core:license_lockout'), response.url)

        # Lockout screen itself renders HTTP 200
        lockout_resp = self.client.get(reverse('core:license_lockout'))
        self.assertEqual(lockout_resp.status_code, 200)
        self.assertContains(lockout_resp, "Software License Activation Required")

    def test_activation_unlocks_system(self):
        """Verify submitting valid license key unlocks the system immediately"""
        from core import licensing
        from core.models import SoftwareLicense
        from django.utils import timezone
        import datetime

        license_obj = SoftwareLicense.get_license()
        license_obj.installation_id = 'INST-TEST-1234'
        license_obj.trial_start_date = timezone.now() - datetime.timedelta(days=10)
        license_obj.trial_end_date = timezone.now() - datetime.timedelta(days=3)
        license_obj.status = 'TRIAL_EXPIRED'
        license_obj.license_key = ''
        license_obj.save()

        # Generate valid key
        payload = licensing.create_license_payload(
            school_code='HPS-DELHI',
            school_name='Horizon Public School',
            plan_type='ENTERPRISE',
            is_lifetime=True
        )
        valid_key = licensing.sign_license_payload(payload)

        # Submit key to activation view
        self.client.login(email='admin@horizon.edu', password=self.password)
        resp = self.client.post(
            reverse('core:license_activate'),
            {'license_key': valid_key},
            follow=True
        )
        self.assertEqual(resp.status_code, 200)

        license_obj.refresh_from_db()
        self.assertEqual(license_obj.status, 'ACTIVE')
        self.assertEqual(license_obj.license_type, 'ENTERPRISE')

        # Dashboard is now accessible
        dash_resp = self.client.get(reverse('accounts:dashboard_router'), follow=True)
        self.assertEqual(dash_resp.status_code, 200)

    def test_cli_generate_license_command(self):
        """Verify generate_license management command runs successfully"""
        from django.core.management import call_command
        from io import StringIO
        buf = StringIO()
        call_command(
            'generate_license',
            school_code='HPS-DELHI',
            school_name='Horizon Public School',
            days=365,
            plan='PRO',
            stdout=buf
        )
        output = buf.getvalue()
        self.assertIn("HORIZON SOFTWARE MANAGEMENT — LICENSE GENERATOR", output)
        self.assertIn("HRZN.", output)

    def test_one_time_license_activation_and_anti_replay(self):
        """Verify 1-time activation and that expired keys cannot be re-used"""
        from core import licensing
        from core.models import SoftwareLicense, ConsumedLicenseHistory
        import datetime
        from django.utils import timezone

        # 1. Generate a valid 30-day key
        payload = licensing.create_license_payload(
            school_code='HPS-DELHI',
            school_name='Horizon Public School',
            plan_type='STANDARD',
            days=30
        )
        nonce = payload['nonce']
        key = licensing.sign_license_payload(payload)

        # 2. Activate the key -> MUST SUCCEED
        success, msg, _ = licensing.activate_license_key(key, self.school)
        self.assertTrue(success)
        self.assertTrue(ConsumedLicenseHistory.objects.filter(nonce=nonce, is_active=True).exists())

        # 3. Simulate passage of time and mark nonce as consumed/inactive in history
        ConsumedLicenseHistory.objects.filter(nonce=nonce).update(is_active=False)

        # 4. Generate expired key with same consumed nonce
        expired_payload = dict(payload)
        expired_payload['expires'] = (timezone.now().date() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        expired_key = licensing.sign_license_payload(expired_payload)

        # 5. User attempts to re-enter / re-activate the same expired key -> MUST BE REJECTED
        success2, msg2, _ = licensing.activate_license_key(expired_key, self.school)
        self.assertFalse(success2)
        self.assertIn("already been consumed and expired", msg2)


    def test_developer_renewal_with_fresh_nonce(self):
        """Verify developer issuing a new key with a fresh nonce unlocks the expired system"""
        from core import licensing
        from core.models import SoftwareLicense
        import datetime
        from django.utils import timezone

        # Old expired key
        old_payload = licensing.create_license_payload(school_code='HPS-DELHI', days=30)
        old_key = licensing.sign_license_payload(old_payload)
        licensing.activate_license_key(old_key, self.school)

        # Force expire old key
        license_obj = SoftwareLicense.get_license()
        license_obj.valid_until = timezone.now().date() - datetime.timedelta(days=1)
        license_obj.save()
        licensing.evaluate_system_license()

        # Developer generates a NEW renewal key (with new nonce and future 365 days expiry)
        new_payload = licensing.create_license_payload(
            school_code='HPS-DELHI',
            school_name='Horizon Public School',
            plan_type='PRO',
            days=365
        )
        self.assertNotEqual(old_payload['nonce'], new_payload['nonce'])
        new_key = licensing.sign_license_payload(new_payload)

        # Client activates the new renewal key -> MUST SUCCEED
        success, msg, _ = licensing.activate_license_key(new_key, self.school)
        self.assertTrue(success)
        
        eval_res = licensing.evaluate_system_license()
        self.assertTrue(eval_res['is_active'])
        self.assertFalse(eval_res['is_expired'])
        self.assertEqual(eval_res['plan_type'], 'PRO')

    def test_revoke_license_command_and_kill_switch(self):
        """Verify developer can revoke license via CLI or cryptographic kill switch"""
        from core import licensing
        from core.models import SoftwareLicense
        from django.core.management import call_command
        from io import StringIO

        # 1. Activate a valid license
        payload = licensing.create_license_payload(school_code='HPS-DELHI', days=365)
        key = licensing.sign_license_payload(payload)
        licensing.activate_license_key(key, self.school)
        self.assertTrue(licensing.evaluate_system_license()['is_active'])

        # 2. Developer runs revoke_license management command
        buf = StringIO()
        call_command('revoke_license', reason='Subscription Canceled', stdout=buf)
        self.assertIn("LICENSE DEACTIVATOR", buf.getvalue())

        # 3. System is now locked
        eval_res = licensing.evaluate_system_license()
        self.assertFalse(eval_res['is_active'])
        self.assertEqual(eval_res['status'], 'REVOKED')

        # 4. Test cryptographic revocation kill switch token
        # First reactivate
        new_payload = licensing.create_license_payload(school_code='HPS-DELHI', days=365)
        new_key = licensing.sign_license_payload(new_payload)
        licensing.activate_license_key(new_key, self.school)
        self.assertTrue(licensing.evaluate_system_license()['is_active'])

        # Developer generates revocation key
        revoke_payload = licensing.create_license_payload(school_code='HPS-DELHI', plan_type='REVOKED')
        revoke_key = licensing.sign_license_payload(revoke_payload)

        # Applying revocation key locks system
        licensing.activate_license_key(revoke_key, self.school)
        eval_res2 = licensing.evaluate_system_license()
        self.assertFalse(eval_res2['is_active'])
        self.assertEqual(eval_res2['status'], 'REVOKED')





