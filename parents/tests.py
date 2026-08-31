from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from students.models import Student
from parents.models import ParentProfile, ParentStudent

class ParentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='User'
        )
        
        self.parent_user = User.objects.create_user(
            email='david.vance@example.com', password=self.password, first_name='David', last_name='Vance', user_type=UserRole.PARENT
        )
        self.parent_profile = ParentProfile.objects.create(
            user=self.parent_user, first_name='David', last_name='Vance', primary_phone='+1 (555) 777-8888', residential_address='123 Oak St'
        )

        self.child1 = Student.objects.create(
            admission_number='ADM-2026-0010', student_id='STU-1010', first_name='Lucas', last_name='Vance',
            gender='MALE', date_of_birth='2010-02-02', admission_date=timezone.now().date(),
            residential_address='123 Oak St', emergency_contact_name='David Vance', emergency_contact_phone='555-777-8888',
            emergency_contact_relation='Father'
        )
        self.child2 = Student.objects.create(
            admission_number='ADM-2026-0011', student_id='STU-1011', first_name='Chloe', last_name='Vance',
            gender='FEMALE', date_of_birth='2012-07-07', admission_date=timezone.now().date(),
            residential_address='123 Oak St', emergency_contact_name='David Vance', emergency_contact_phone='555-777-8888',
            emergency_contact_relation='Father'
        )

        ParentStudent.objects.create(parent=self.parent_profile, student=self.child1, relationship_type='FATHER', is_primary_contact=True)
        ParentStudent.objects.create(parent=self.parent_profile, student=self.child2, relationship_type='FATHER', is_primary_contact=False)

    def test_multi_child_relationship(self):
        """Verify parent profile returns all linked children"""
        children = self.parent_profile.children
        self.assertEqual(len(children), 2)
        self.assertIn(self.child1, children)
        self.assertIn(self.child2, children)

    def test_parent_switch_child_portal(self):
        """Verify parent child switching stores active child in session securely"""
        self.client.login(email='david.vance@example.com', password=self.password)
        
        # Switch to Child 2
        response = self.client.post(reverse('parents:switch_child', kwargs={'child_id': self.child2.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get('active_child_id'), str(self.child2.pk))

    def test_unauthorized_child_switch_prevention(self):
        """Verify parent cannot switch to an unlinked student ID (Object-Level Access Control)"""
        other_child = Student.objects.create(
            admission_number='ADM-2026-0099', student_id='STU-1099', first_name='Stranger', last_name='Student',
            gender='MALE', date_of_birth='2010-01-01', admission_date=timezone.now().date(),
            residential_address='999 Foreign St', emergency_contact_name='Other', emergency_contact_phone='111', emergency_contact_relation='Other'
        )
        self.client.login(email='david.vance@example.com', password=self.password)
        
        self.client.post(reverse('parents:switch_child', kwargs={'child_id': other_child.pk}))
        # Session should NOT switch to other_child
        self.assertNotEqual(self.client.session.get('active_child_id'), str(other_child.pk))

    def test_admin_link_student_to_parent(self):
        """Verify school admin can link an additional student to a parent profile"""
        self.client.login(email='admin@school.edu', password=self.password)
        new_child = Student.objects.create(
            admission_number='ADM-2026-0033', student_id='STU-1033', first_name='Maya', last_name='Vance',
            gender='FEMALE', date_of_birth='2014-04-04', admission_date=timezone.now().date(),
            residential_address='123 Oak St', emergency_contact_name='David Vance', emergency_contact_phone='555-777-8888',
            emergency_contact_relation='Father'
        )

        response = self.client.post(
            reverse('parents:link_student', kwargs={'pk': self.parent_profile.pk}),
            {
                'student': str(new_child.pk),
                'relationship_type': 'FATHER',
                'is_primary_contact': 'on',
                'can_pickup_child': 'on'
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ParentStudent.objects.filter(parent=self.parent_profile, student=new_child).exists())
        self.assertIn(new_child, self.parent_profile.children)

    def test_admin_unlink_student_from_parent(self):
        """Verify school admin can unlink a student from a parent profile"""
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(
            reverse('parents:unlink_student', kwargs={'pk': self.parent_profile.pk, 'student_id': self.child1.pk}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ParentStudent.objects.filter(parent=self.parent_profile, student=self.child1).exists())
        self.assertNotIn(self.child1, self.parent_profile.children)

    def test_parent_apply_ward_leave(self):
        """Verify parent can apply for leave for their active ward"""
        from leave.models import LeaveType, LeaveRequest
        leave_type = LeaveType.objects.create(name='Medical Leave', allocated_days_per_year=10)

        self.client.login(email='david.vance@example.com', password=self.password)

        today = timezone.now().date()
        resp = self.client.post(reverse('parents:ward_leave'), {
            'leave_type': str(leave_type.id),
            'start_date': str(today),
            'end_date': str(today),
            'reason': 'Viral fever and doctor checkup.'
        }, follow=True)

        self.assertEqual(resp.status_code, 200)
        leave = LeaveRequest.objects.filter(leave_type=leave_type).first()
        self.assertIsNotNone(leave)
        self.assertIn('Lucas', leave.reason)

    def test_parent_ward_timetable_view(self):
        """Verify parent can view timetable for their child"""
        self.client.login(email='david.vance@example.com', password=self.password)
        resp = self.client.get(reverse('parents:ward_timetable'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Lucas Vance's Weekly Class Timetable")

