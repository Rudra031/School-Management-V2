from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from communication.models import Notice, InAppNotification

class CommunicationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='Staff'
        )
        self.teacher = User.objects.create_user(
            email='teacher@school.edu', password=self.password, first_name='Teacher', last_name='User', user_type=UserRole.TEACHER
        )
        self.student = User.objects.create_user(
            email='student@school.edu', password=self.password, first_name='Student', last_name='User', user_type=UserRole.STUDENT
        )

        # Public Notice
        self.notice_all = Notice.objects.create(
            title='Annual Sports Day 2026',
            content='All students and faculty are invited.',
            target_audience=Notice.Audience.ALL,
            created_by=self.admin
        )
        # Teacher Only Notice
        self.notice_teacher = Notice.objects.create(
            title='Faculty Staff Meeting',
            content='Mandatory curriculum review at 3 PM.',
            target_audience=Notice.Audience.TEACHERS,
            created_by=self.admin
        )

    def test_notice_board_audience_filtering(self):
        """Verify teacher sees teacher notices, student only sees public notices"""
        # Teacher logs in
        self.client.login(email='teacher@school.edu', password=self.password)
        resp_teacher = self.client.get(reverse('communication:notice_board'))
        self.assertEqual(resp_teacher.status_code, 200)
        self.assertEqual(len(resp_teacher.context['notices']), 2)

        # Student logs in
        self.client.login(email='student@school.edu', password=self.password)
        resp_student = self.client.get(reverse('communication:notice_board'))
        self.assertEqual(resp_student.status_code, 200)
        self.assertEqual(len(resp_student.context['notices']), 1)
        self.assertEqual(resp_student.context['notices'][0].title, 'Annual Sports Day 2026')

    def test_in_app_notification_read_workflow(self):
        """Verify user receiving and marking notifications as read"""
        notif = InAppNotification.objects.create(
            recipient=self.student,
            title='New Assignment Uploaded',
            message='Physics homework has been posted.',
            is_read=False
        )
        self.client.login(email='student@school.edu', password=self.password)
        resp = self.client.get(reverse('communication:notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['notifications']), 1)

        # Mark as read
        resp_read = self.client.post(reverse('communication:notification_read', kwargs={'pk': notif.pk}), follow=True)
        self.assertEqual(resp_read.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
