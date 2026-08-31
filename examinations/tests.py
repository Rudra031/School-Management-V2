from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section, Subject
from students.models import Student, StudentEnrollment
from fees.models import StudentFeeInvoice
from examinations.models import GradeScale, ExamTerm, ExamSchedule, ExamMarkEntry

class ExaminationsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.teacher_user = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='Exam', user_type=UserRole.TEACHER
        )
        self.admin_user = User.objects.create_user(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='User', user_type=UserRole.ADMIN
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.class10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.class10, name='A')
        self.math = Subject.objects.create(name='Mathematics', code='MATH-10')

        # Grade Scale
        self.grade_a = GradeScale.objects.create(name='Scale', min_percentage=80.0, max_percentage=100.0, grade_letter='A', grade_point=4.0)
        self.grade_b = GradeScale.objects.create(name='Scale', min_percentage=60.0, max_percentage=79.99, grade_letter='B', grade_point=3.0)
        self.grade_c = GradeScale.objects.create(name='Scale', min_percentage=33.0, max_percentage=59.99, grade_letter='C', grade_point=2.0)

        self.student = Student.objects.create(
            admission_number='ADM-200', student_id='STU-200', first_name='Sherlock', last_name='Holmes',
            gender='MALE', date_of_birth='2010-01-06', admission_date=today,
            residential_address='221B Baker St', emergency_contact_name='John Watson', emergency_contact_phone='999', emergency_contact_relation='Associate'
        )
        self.enrollment = StudentEnrollment.objects.create(
            student=self.student, academic_year=self.year, section=self.sec_a, roll_number=1, is_current=True
        )

        self.term = ExamTerm.objects.create(
            academic_year=self.year, title='Term 1 Midterms', term_type=ExamTerm.TermType.HALF_YEARLY,
            start_date=today, end_date=today + timedelta(days=10), requires_fee_clearance=True, is_published=True
        )
        self.schedule = ExamSchedule.objects.create(
            exam_term=self.term, class_level=self.class10, subject=self.math,
            exam_date=today, start_time='09:00:00', duration_minutes=180, room_number='Hall A',
            max_marks=Decimal('100.00'), pass_marks=Decimal('33.00'),
            theory_marks_max=Decimal('70.00'), practical_marks_max=Decimal('20.00'), internal_marks_max=Decimal('10.00')
        )

    def test_multi_component_mark_entry(self):
        """Verify automated grade resolution with theory, practical, internal, and grace marks"""
        entry = ExamMarkEntry.objects.create(
            exam_schedule=self.schedule,
            student_enrollment=self.enrollment,
            theory_marks_obtained=Decimal('60.00'),
            practical_marks_obtained=Decimal('18.00'),
            internal_marks_obtained=Decimal('9.00'),
            grace_marks=Decimal('2.00'),
        )
        self.assertEqual(entry.total_marks_obtained, Decimal('89.00'))
        self.assertEqual(entry.percentage, Decimal('89.00'))
        self.assertTrue(entry.is_passed)
        self.assertEqual(entry.grade, self.grade_a)

    def test_admit_card_with_fee_clearance_guard(self):
        """Verify Admit Card checks fee clearance status"""
        # Create an unpaid invoice
        StudentFeeInvoice.objects.create(
            invoice_number='INV-DUE-01',
            student_enrollment=self.enrollment,
            academic_year=self.year,
            title='Term Dues',
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            total_amount=Decimal('500.00'),
            balance_amount=Decimal('500.00')
        )
        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.get(reverse('examinations:admit_card') + f'?student_id={self.student.id}&term_id={self.term.id}')
        self.assertEqual(resp.status_code, 200)
        card_data = resp.context['cards'][0]
        self.assertFalse(card_data['fee_cleared'])
        self.assertEqual(card_data['fee_due'], Decimal('500.00'))

    def test_tabulation_sheet_and_promotion_views(self):
        """Verify Tabulation sheet calculations and Academic Promotion view"""
        ExamMarkEntry.objects.create(
            exam_schedule=self.schedule,
            student_enrollment=self.enrollment,
            theory_marks_obtained=Decimal('65.00'),
            practical_marks_obtained=Decimal('18.00'),
            internal_marks_obtained=Decimal('8.00'),
        )
        self.client.login(email='admin@school.edu', password=self.password)
        
        # Tabulation sheet
        resp_tab = self.client.get(reverse('examinations:tabulation_sheet') + f'?term={self.term.id}&section={self.sec_a.id}')
        self.assertEqual(resp_tab.status_code, 200)
        self.assertEqual(resp_tab.context['total_students'], 1)
        self.assertEqual(resp_tab.context['passed_count'], 1)

        # Promotion view
        resp_prom = self.client.get(reverse('examinations:academic_promotion') + f'?section={self.sec_a.id}')
        self.assertEqual(resp_prom.status_code, 200)

        # Report card view
        resp_rc = self.client.get(reverse('examinations:report_card', kwargs={'pk': self.student.pk}) + f'?term={self.term.id}')
        self.assertEqual(resp_rc.status_code, 200)
        self.assertEqual(resp_rc.context['total_obtained'], Decimal('91.00'))

