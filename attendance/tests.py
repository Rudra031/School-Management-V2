from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from attendance.models import StudentAttendanceSheet, StudentAttendanceRecord

class AttendanceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.teacher_user = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='One', user_type=UserRole.TEACHER
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.class10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.class10, name='A')

        self.student = Student.objects.create(
            admission_number='ADM-100', student_id='STU-100', first_name='Arthur', last_name='Dent',
            gender='MALE', date_of_birth='2010-01-01', admission_date=today,
            residential_address='Earth', emergency_contact_name='Ford', emergency_contact_phone='123', emergency_contact_relation='Friend'
        )
        self.enrollment = StudentEnrollment.objects.create(
            student=self.student, academic_year=self.year, section=self.sec_a, roll_number=1, is_current=True
        )

    def test_daily_attendance_marking_flow(self):
        """Verify teacher can mark section attendance and save records atomically"""
        self.client.login(email='teacher@school.edu', password=self.password)
        today_str = timezone.now().date().strftime('%Y-%m-%d')
        
        # Post attendance marking
        response = self.client.post(reverse('attendance:mark'), {
            'section_id': str(self.sec_a.id),
            'date': today_str,
            f'status_{self.enrollment.id}': 'PRESENT',
            f'remarks_{self.enrollment.id}': 'On time',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify Attendance Sheet & Record
        sheet = StudentAttendanceSheet.objects.filter(section=self.sec_a, date=today_str).first()
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet.present_count, 1)

        record = StudentAttendanceRecord.objects.filter(sheet=sheet, student_enrollment=self.enrollment).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, StudentAttendanceRecord.Status.PRESENT)
        self.assertEqual(record.remarks, 'On time')

    def test_attendance_report_view(self):
        """Verify monthly attendance report calculates student percentage"""
        sheet = StudentAttendanceSheet.objects.create(
            academic_year=self.year, section=self.sec_a, date=timezone.now().date()
        )
        StudentAttendanceRecord.objects.create(
            sheet=sheet, student_enrollment=self.enrollment, status=StudentAttendanceRecord.Status.PRESENT
        )

        self.client.login(email='teacher@school.edu', password=self.password)
        resp = self.client.get(reverse('attendance:report') + f'?section={self.sec_a.id}')
        self.assertIn('report_rows', resp.context)
        self.assertEqual(resp.context['report_rows'][0]['percentage'], 100.0)

    def test_monthly_matrix_view(self):
        """Verify monthly attendance matrix renders all calendar days and students"""
        self.client.login(email='teacher@school.edu', password=self.password)
        resp = self.client.get(reverse('attendance:monthly_matrix') + f'?section={self.sec_a.id}&year=2026&month=8')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('matrix_rows', resp.context)
        self.assertIn('days_header', resp.context)
        self.assertEqual(len(resp.context['matrix_rows']), 1)
        self.assertEqual(len(resp.context['days_header']), 31) # August has 31 days

    def test_attendance_cell_update_api(self):
        """Verify AJAX endpoint for 1-click status cycling on matrix cells"""
        self.client.login(email='teacher@school.edu', password=self.password)
        today_str = timezone.now().date().strftime('%Y-%m-%d')
        
        # Test setting status to LATE
        resp = self.client.post(
            reverse('attendance:api_update_cell'),
            data={'enrollment_id': str(self.enrollment.id), 'date': today_str, 'status': 'LATE'},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'LATE')
        self.assertEqual(data['letter'], 'L')

        # Verify persisted in database
        rec = StudentAttendanceRecord.objects.filter(student_enrollment=self.enrollment, sheet__date=today_str).first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, StudentAttendanceRecord.Status.LATE)

