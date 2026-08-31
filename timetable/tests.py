from datetime import time, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section, Subject
from staff.models import StaffMember, Designation
from timetable.models import TimeSlot, ClassTimetable
from timetable.forms import ClassTimetableForm

class TimetableTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='User'
        )
        self.teacher_user = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='John', last_name='Doe', user_type=UserRole.TEACHER
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.grade10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.grade10, name='A')
        self.sec_b = Section.objects.create(class_level=self.grade10, name='B')

        self.desig = Designation.objects.create(title='Math Teacher', is_teaching_role=True)
        self.teacher = StaffMember.objects.create(
            user=self.teacher_user, employee_id='EMP-001', designation=self.desig,
            first_name='John', last_name='Doe', gender='MALE', joining_date=today
        )

        self.math = Subject.objects.create(name='Mathematics', code='MATH-10')
        self.science = Subject.objects.create(name='Science', code='SCI-10')

        self.slot1 = TimeSlot.objects.create(
            academic_year=self.year, period_number=1, name='Period 1', start_time=time(8, 30), end_time=time(9, 15)
        )

    def test_timetable_entry_and_collision_prevention(self):
        """Verify timetable creation and conflict detection for teacher and section"""
        # Create initial entry
        entry = ClassTimetable.objects.create(
            academic_year=self.year, section=self.sec_a, day_of_week=1,
            time_slot=self.slot1, subject=self.math, teacher=self.teacher, room_number='Room 101'
        )
        self.assertEqual(entry.section, self.sec_a)

        # Form testing section collision
        form_sec_collision = ClassTimetableForm(data={
            'academic_year': self.year.id,
            'section': self.sec_a.id,
            'day_of_week': 1,
            'time_slot': self.slot1.id,
            'subject': self.science.id,
            'teacher': self.teacher.id,
            'room_number': 'Room 102',
        })
        self.assertFalse(form_sec_collision.is_valid())
        self.assertIn('time_slot', form_sec_collision.errors)

        # Form testing teacher collision in different section
        form_teacher_collision = ClassTimetableForm(data={
            'academic_year': self.year.id,
            'section': self.sec_b.id,
            'day_of_week': 1,
            'time_slot': self.slot1.id,
            'subject': self.science.id,
            'teacher': self.teacher.id,
            'room_number': 'Room 103',
        })
        self.assertFalse(form_teacher_collision.is_valid())
        self.assertIn('teacher', form_teacher_collision.errors)

    def test_timetable_grid_view_renders(self):
        """Verify timetable overview matrix view response"""
        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.get(reverse('timetable:overview') + f'?section={self.sec_a.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('grid', resp.context)
