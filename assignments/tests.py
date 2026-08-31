from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section, Subject
from staff.models import StaffMember, Designation
from students.models import Student, StudentEnrollment
from assignments.models import Assignment, AssignmentSubmission

class AssignmentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.teacher_user = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='HW', user_type=UserRole.TEACHER
        )
        self.student_user = User.objects.create_user(
            email='student@school.edu', password=self.password, first_name='Harry', last_name='Potter', user_type=UserRole.STUDENT
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.class10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.class10, name='A')
        self.math = Subject.objects.create(name='Mathematics', code='MATH-10')

        self.desig = Designation.objects.create(title='Faculty', is_teaching_role=True)
        self.teacher = StaffMember.objects.create(
            user=self.teacher_user, employee_id='EMP-300', designation=self.desig,
            first_name='Teacher', last_name='HW', gender='FEMALE', joining_date=today
        )

        self.student = Student.objects.create(
            user=self.student_user, admission_number='ADM-300', student_id='STU-300', first_name='Harry', last_name='Potter',
            gender='MALE', date_of_birth='2010-07-31', admission_date=today,
            residential_address='4 Privet Drive', emergency_contact_name='Sirius', emergency_contact_phone='777', emergency_contact_relation='Godfather'
        )
        self.enrollment = StudentEnrollment.objects.create(
            student=self.student, academic_year=self.year, section=self.sec_a, roll_number=7, is_current=True
        )

        self.assignment = Assignment.objects.create(
            academic_year=self.year, section=self.sec_a, subject=self.math, teacher=self.teacher,
            title='Algebra Chapter 2 Problem Set', description='Complete problems 1 through 15',
            assigned_date=today, due_date=timezone.now() + timedelta(days=5), max_points=Decimal('100.00'),
            status=Assignment.Status.PUBLISHED
        )

    def test_student_homework_submission_flow(self):
        """Verify student can submit homework notes and file"""
        self.client.login(email='student@school.edu', password=self.password)
        resp = self.client.post(reverse('assignments:submit', kwargs={'pk': self.assignment.pk}), {
            'submission_text': 'All 15 problems solved with step-by-step proofs.',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        submission = AssignmentSubmission.objects.filter(assignment=self.assignment, student_enrollment=self.enrollment).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.status, AssignmentSubmission.Status.SUBMITTED)
        self.assertIn('step-by-step', submission.submission_text)

    def test_teacher_grading_workflow(self):
        """Verify teacher can evaluate student submission and assign score and feedback"""
        submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student_enrollment=self.enrollment,
            submission_text='Submitted homework draft'
        )

        self.client.login(email='teacher@school.edu', password=self.password)
        resp = self.client.post(reverse('assignments:grade_submission', kwargs={'pk': submission.pk}), {
            'score_obtained': '95.0',
            'feedback': 'Excellent mathematical reasoning.',
            'status': 'GRADED',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        submission.refresh_from_db()
        self.assertEqual(submission.score_obtained, Decimal('95.0'))
        self.assertEqual(submission.status, AssignmentSubmission.Status.GRADED)
        self.assertEqual(submission.graded_by, self.teacher_user)
