from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from admissions.models import AdmissionsApplication

class AdmissionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='Officer'
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.grade1 = ClassLevel.objects.create(name='Grade 1', numeric_level=1)
        self.sec_a = Section.objects.create(class_level=self.grade1, name='A')

    def test_admissions_application_and_student_conversion(self):
        """Verify submitting an admission application and converting accepted applicant to enrolled student"""
        app = AdmissionsApplication.objects.create(
            application_number='APP-2026-0001',
            academic_year=self.year,
            applying_for_class=self.grade1,
            first_name='Peter',
            last_name='Parker',
            gender='MALE',
            date_of_birth='2019-08-10',
            parent_name='May Parker',
            parent_phone='+1 (555) 999-0000',
            parent_email='may.parker@example.com',
            residential_address='20 Ingram St, Queens',
            status=AdmissionsApplication.Stage.ACCEPTED
        )

        self.client.login(email='admin@school.edu', password=self.password)
        
        # Post conversion to enrolled student
        response = self.client.post(reverse('admissions:convert_student', kwargs={'pk': app.pk}), {
            'section': str(self.sec_a.id),
            'roll_number': 15,
            'admission_number': 'ADM-2026-0999',
            'student_id': 'STU-2026-0999',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify Student and Enrollment records exist
        student = Student.objects.filter(admission_number='ADM-2026-0999').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.full_name, 'Peter Parker')

        enrollment = StudentEnrollment.objects.filter(student=student, academic_year=self.year).first()
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.section, self.sec_a)
        self.assertEqual(enrollment.roll_number, 15)

        # Verify application marked as ENROLLED
        app.refresh_from_db()
        self.assertEqual(app.status, AdmissionsApplication.Stage.ENROLLED)

    def test_quick_admission_enroll_and_continue_full_process(self):
        """Verify quick admission with enroll_and_continue flow seamlessly continues into full admission"""
        self.client.login(email='admin@school.edu', password=self.password)

        # 1. Submit Quick Admission with action='enroll_and_continue'
        resp = self.client.post(reverse('admissions:quick_admission'), {
            'first_name': 'Rohan',
            'last_name': 'Verma',
            'date_of_birth': '2015-06-20',
            'gender': 'MALE',
            'applying_for_class': str(self.grade1.id),
            'section': str(self.sec_a.id),
            'academic_year': str(self.year.id),
            'parent_name': 'Sanjay Verma',
            'parent_phone': '+91-9876543210',
            'parent_email': 'sanjay.verma@example.com',
            'residential_address': 'Sector 21, Chandigarh',
            'action': 'enroll_and_continue'
        }, follow=False)

        self.assertEqual(resp.status_code, 302)
        app = AdmissionsApplication.objects.filter(first_name='Rohan', last_name='Verma').first()
        self.assertIsNotNone(app)
        self.assertIn(f"?app_id={app.id}", resp.url)

        student = Student.objects.filter(first_name='Rohan', last_name='Verma').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.status, Student.Status.ACTIVE)

        # 2. Open Full Admission Wizard with ?app_id
        wizard_resp = self.client.get(reverse('admissions:full_admission') + f"?app_id={app.id}")
        self.assertEqual(wizard_resp.status_code, 200)
        self.assertEqual(wizard_resp.context['existing_app'].id, app.id)
        self.assertContains(wizard_resp, "Continuing Full Admission Profile: Rohan Verma")

        # 3. Submit Full Admission Dossier updating details
        post_resp = self.client.post(reverse('admissions:full_admission'), {
            'existing_app_id': str(app.id),
            'first_name': 'Rohan',
            'last_name': 'Verma',
            'gender': 'MALE',
            'date_of_birth': '2015-06-20',
            'blood_group': 'O+',
            'religion': 'Hindi',
            'nationality': 'Indian',
            'father_name': 'Sanjay Verma',
            'father_phone': '+91-9876543210',
            'mother_name': 'Pooja Verma',
            'mother_phone': '+91-9876543211',
            'parent_name': 'Sanjay Verma',
            'parent_phone': '+91-9876543210',
            'parent_email': 'sanjay.verma@example.com',
            'residential_address': 'Sector 21, Chandigarh',
            'previous_school_name': 'Delhi Public School',
            'applying_for_class': str(self.grade1.id),
            'section': str(self.sec_a.id),
            'academic_year': str(self.year.id),
        }, follow=True)

        self.assertEqual(post_resp.status_code, 200)
        # Ensure no duplicate student was created
        self.assertEqual(Student.objects.filter(first_name='Rohan', last_name='Verma').count(), 1)
        student.refresh_from_db()
        self.assertEqual(student.blood_group, 'O+')
        self.assertEqual(student.nationality, 'Indian')

    def test_quick_admission_finish_shows_continue_link_on_success(self):
        """Verify quick admission success page provides continue full admission option"""
        self.client.login(email='admin@school.edu', password=self.password)

        resp = self.client.post(reverse('admissions:quick_admission'), {
            'first_name': 'Ananya',
            'last_name': 'Iyer',
            'date_of_birth': '2016-03-15',
            'gender': 'FEMALE',
            'applying_for_class': str(self.grade1.id),
            'section': str(self.sec_a.id),
            'academic_year': str(self.year.id),
            'parent_name': 'Ramesh Iyer',
            'parent_phone': '+91-9811122233',
            'parent_email': 'ramesh.iyer@example.com',
            'residential_address': 'Indiranagar, Bangalore',
            'action': 'enroll'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        app = AdmissionsApplication.objects.filter(first_name='Ananya', last_name='Iyer').first()
        self.assertIsNotNone(app)
        self.assertContains(resp, f"/admissions/full/?app_id={app.id}")
        self.assertContains(resp, "Continue Full Admission")

