from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from leave.models import LeaveType, LeaveRequest

class LeaveTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='Officer'
        )
        self.teacher = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='Applicant', user_type=UserRole.TEACHER
        )

        self.sick_leave = LeaveType.objects.create(name='Sick Leave', allocated_days_per_year=10)

    def test_leave_application_and_approval_workflow(self):
        """Verify staff applying for leave and admin approving request"""
        today = timezone.now().date()
        leave_req = LeaveRequest.objects.create(
            user=self.teacher,
            leave_type=self.sick_leave,
            start_date=today,
            end_date=today + timedelta(days=2),
            reason='Flu and high fever',
            status=LeaveRequest.Status.PENDING
        )
        self.assertEqual(leave_req.total_days, 3)

        # Admin approves leave
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(reverse('leave:review', kwargs={'pk': leave_req.pk}), {
            'action': 'APPROVE',
            'review_remarks': 'Get well soon. Approved.',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave_req.reviewed_by, self.admin)
