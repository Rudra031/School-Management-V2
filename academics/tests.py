from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, UserRole
from academics.models import AcademicYear, Department, ClassLevel, Section, Subject, SubjectTeacherAllocation
from staff.models import StaffMember, Designation

class AcademicsTestCase(TestCase):
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
        self.year1 = AcademicYear.objects.create(
            name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True
        )
        self.year2 = AcademicYear.objects.create(
            name='2026-2027', start_date=today + timedelta(days=366), end_date=today + timedelta(days=730), is_current=False
        )

        self.dept = Department.objects.create(name='Mathematics & Science', code='MATH-SCI')
        self.grade10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10, department=self.dept)
        self.sec_a = Section.objects.create(class_level=self.grade10, name='A', room_number='Room 101')

        self.desig = Designation.objects.create(title='PGT Mathematics', is_teaching_role=True)
        self.staff = StaffMember.objects.create(
            user=self.teacher_user, employee_id='EMP-001', designation=self.desig,
            first_name='John', last_name='Doe', gender='MALE', joining_date=today
        )
        self.subject = Subject.objects.create(name='Mathematics', code='MATH-10', department=self.dept)

    def test_academic_year_active_toggle(self):
        """Verify setting year2 as current resets year1"""
        self.assertTrue(self.year1.is_current)
        self.assertFalse(self.year2.is_current)

        self.year2.is_current = True
        self.year2.save()

        self.year1.refresh_from_db()
        self.assertFalse(self.year1.is_current)
        self.assertTrue(self.year2.is_current)

    def test_class_section_hierarchy(self):
        """Verify section full name and class association"""
        self.assertEqual(self.sec_a.full_name, "Grade 10 (A)")
        self.assertEqual(self.grade10.total_sections, 1)

    def test_teacher_allocation(self):
        """Verify assigning teacher to subject and section"""
        alloc = SubjectTeacherAllocation.objects.create(
            academic_year=self.year1, section=self.sec_a, subject=self.subject, teacher=self.staff
        )
        self.assertEqual(alloc.teacher.full_name, "John Doe")
        self.assertEqual(alloc.subject.code, "MATH-10")

    def test_academic_overview_access(self):
        """Admin can access overview, teacher cannot without permission"""
        self.client.login(email='admin@school.edu', password=self.password)
        resp = self.client.get(reverse('academics:overview'))
        self.assertEqual(resp.status_code, 200)

        self.client.login(email='teacher@school.edu', password=self.password)
        resp = self.client.get(reverse('academics:overview'))
        self.assertEqual(resp.status_code, 403)

    def test_class_crud_operations(self):
        """Verify adding, editing, and deleting a ClassLevel"""
        self.client.login(email='admin@school.edu', password=self.password)
        
        # 1. Create Class
        resp_create = self.client.post(reverse('academics:class_create'), {
            'name': 'Grade 11',
            'numeric_level': 11,
            'department': str(self.dept.id),
            'description': 'Senior Secondary Class 11'
        }, follow=True)
        self.assertEqual(resp_create.status_code, 200)
        grade11 = ClassLevel.objects.filter(numeric_level=11).first()
        self.assertIsNotNone(grade11)
        self.assertEqual(grade11.name, 'Grade 11')

        # 2. Edit Class
        resp_edit = self.client.post(reverse('academics:class_edit', kwargs={'pk': grade11.pk}), {
            'name': 'Class XI (Senior)',
            'numeric_level': 11,
            'department': str(self.dept.id),
            'description': 'Senior Secondary'
        }, follow=True)
        self.assertEqual(resp_edit.status_code, 200)
        grade11.refresh_from_db()
        self.assertEqual(grade11.name, 'Class XI (Senior)')

        # 3. Delete Class
        resp_del = self.client.post(reverse('academics:class_delete', kwargs={'pk': grade11.pk}), follow=True)
        self.assertEqual(resp_del.status_code, 200)
        grade11.refresh_from_db()
        self.assertTrue(grade11.is_deleted)

    def test_section_crud_operations(self):
        """Verify adding, editing, and deleting a Section"""
        self.client.login(email='admin@school.edu', password=self.password)

        # 1. Create Section
        resp_create = self.client.post(reverse('academics:section_create'), {
            'class_level': str(self.grade10.id),
            'name': 'B',
            'room_number': 'Room 102',
            'class_teacher': str(self.staff.id),
            'max_capacity': 45
        }, follow=True)
        self.assertEqual(resp_create.status_code, 200)
        sec_b = Section.objects.filter(class_level=self.grade10, name='B').first()
        self.assertIsNotNone(sec_b)
        self.assertEqual(sec_b.max_capacity, 45)

        # 2. Edit Section
        resp_edit = self.client.post(reverse('academics:section_edit', kwargs={'pk': sec_b.pk}), {
            'class_level': str(self.grade10.id),
            'name': 'B-Science',
            'room_number': 'Lab 1',
            'class_teacher': str(self.staff.id),
            'max_capacity': 40
        }, follow=True)
        self.assertEqual(resp_edit.status_code, 200)
        sec_b.refresh_from_db()
        self.assertEqual(sec_b.name, 'B-Science')

        # 3. Delete Section
        resp_del = self.client.post(reverse('academics:section_delete', kwargs={'pk': sec_b.pk}), follow=True)
        self.assertEqual(resp_del.status_code, 200)
        sec_b.refresh_from_db()
        self.assertTrue(sec_b.is_deleted)

    def test_subject_crud_operations(self):
        """Verify adding, editing, and deleting a Subject"""
        self.client.login(email='admin@school.edu', password=self.password)

        # 1. Create Subject
        resp_create = self.client.post(reverse('academics:subject_create'), {
            'name': 'Physics',
            'code': 'PHY-101',
            'subject_type': 'BOTH',
            'department': str(self.dept.id),
            'credit_hours': '4.0',
            'description': 'General Physics with practicals'
        }, follow=True)
        self.assertEqual(resp_create.status_code, 200)
        phys = Subject.objects.filter(code='PHY-101').first()
        self.assertIsNotNone(phys)

        # 2. Edit Subject
        resp_edit = self.client.post(reverse('academics:subject_edit', kwargs={'pk': phys.pk}), {
            'name': 'Advanced Physics',
            'code': 'PHY-101',
            'subject_type': 'BOTH',
            'department': str(self.dept.id),
            'credit_hours': '4.5',
            'description': 'Advanced Physics'
        }, follow=True)
        self.assertEqual(resp_edit.status_code, 200)
        phys.refresh_from_db()
        self.assertEqual(phys.name, 'Advanced Physics')

        # 3. Delete Subject
        resp_del = self.client.post(reverse('academics:subject_delete', kwargs={'pk': phys.pk}), follow=True)
        self.assertEqual(resp_del.status_code, 200)
        phys.refresh_from_db()
        self.assertTrue(phys.is_deleted)

