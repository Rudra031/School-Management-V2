from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment, StudentHealthRecord, StudentMedicalIncident

class StudentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='User'
        )
        self.teacher = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='User', user_type=UserRole.TEACHER
        )

        today = timezone.now().date()
        self.year1 = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.year2 = AcademicYear.objects.create(name='2026-2027', start_date=today + timedelta(days=366), end_date=today + timedelta(days=730), is_current=False)

        self.class9 = ClassLevel.objects.create(name='Grade 9', numeric_level=9)
        self.class10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        
        self.sec_9a = Section.objects.create(class_level=self.class9, name='A')
        self.sec_10a = Section.objects.create(class_level=self.class10, name='A')

    def test_student_enrollment_registration(self):
        """Verify student registration atomically creates Student + StudentEnrollment"""
        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.post(reverse('students:student_register'), {
            'admission_number': 'ADM-2026-0001',
            'student_id': 'STU-1001',
            'first_name': 'Lucas',
            'last_name': 'Vance',
            'gender': 'MALE',
            'date_of_birth': '2010-04-12',
            'admission_date': '2026-01-05',
            'residential_address': '123 Forest St',
            'city': 'Metro City',
            'state': 'State',
            'postal_code': '10001',
            'emergency_contact_name': 'David Vance',
            'emergency_contact_phone': '+1 (555) 000-1111',
            'emergency_contact_relation': 'Father',
            'academic_year': str(self.year1.id),
            'section': str(self.sec_9a.id),
            'roll_number': 12,
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        student = Student.objects.filter(admission_number='ADM-2026-0001').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.full_name, 'Lucas Vance')

        enrollment = student.current_enrollment
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.section, self.sec_9a)
        self.assertEqual(enrollment.roll_number, 12)

    def test_student_promotion_wizard(self):
        """Verify promoting a cohort creates new enrollment under new academic year and preserves history"""
        student = Student.objects.create(
            admission_number='ADM-2026-0002',
            student_id='STU-1002',
            first_name='Emma',
            last_name='Watson',
            gender='FEMALE',
            date_of_birth='2010-09-19',
            admission_date=timezone.now().date(),
            residential_address='456 Elm St',
            emergency_contact_name='Chris Watson',
            emergency_contact_phone='555-1234',
            emergency_contact_relation='Mother'
        )
        StudentEnrollment.objects.create(
            student=student,
            academic_year=self.year1,
            section=self.sec_9a,
            roll_number=5,
            enrollment_date=timezone.now().date(),
            is_current=True
        )

        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.post(reverse('students:student_promote'), {
            'from_academic_year': str(self.year1.id),
            'from_section': str(self.sec_9a.id),
            'to_academic_year': str(self.year2.id),
            'to_section': str(self.sec_10a.id),
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Check that previous enrollment is PROMOTED and not current
        old_enrollment = StudentEnrollment.objects.get(student=student, academic_year=self.year1)
        self.assertFalse(old_enrollment.is_current)
        self.assertEqual(old_enrollment.promotion_status, StudentEnrollment.PromotionStatus.PROMOTED)

        # Check new current enrollment
        new_enrollment = StudentEnrollment.objects.get(student=student, academic_year=self.year2)
        self.assertTrue(new_enrollment.is_current)
        self.assertEqual(new_enrollment.section, self.sec_10a)
        self.assertEqual(new_enrollment.roll_number, 5)

    def test_restricted_health_records(self):
        """Verify strict permission control on student health information"""
        student = Student.objects.create(
            admission_number='ADM-2026-0003',
            student_id='STU-1003',
            first_name='Oliver',
            last_name='Queen',
            gender='MALE',
            date_of_birth='2011-01-01',
            admission_date=timezone.now().date(),
            residential_address='789 Starling St',
            emergency_contact_name='Robert Queen',
            emergency_contact_phone='555-9999',
            emergency_contact_relation='Father'
        )

        # Admin access is allowed
        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.get(reverse('students:student_health', kwargs={'pk': student.pk}))
        self.assertEqual(resp.status_code, 200)

        # Teacher access is denied with 403 Forbidden
        self.client.login(email='teacher@school.edu', password=self.password)
        resp = self.client.get(reverse('students:student_health', kwargs={'pk': student.pk}))
        self.assertEqual(resp.status_code, 403)
