from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole

class AccountsAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'SuperSecret123!'
        
        self.superadmin = User.objects.create_superuser(
            username='SUPERADMIN01',
            email='superadmin@school.edu',
            password=self.password,
            first_name='Super',
            last_name='Admin'
        )
        self.principal = User.objects.create_user(
            username='PRIN001',
            email='principal@school.edu',
            password=self.password,
            first_name='Lead',
            last_name='Principal',
            user_type=UserRole.PRINCIPAL
        )
        self.teacher = User.objects.create_user(
            username='TCH_MATH',
            email='teacher@school.edu',
            password=self.password,
            first_name='John',
            last_name='Doe',
            user_type=UserRole.TEACHER
        )
        self.student = User.objects.create_user(
            username='STU2026_01',
            email='student@school.edu',
            password=self.password,
            first_name='Alex',
            last_name='Smith',
            user_type=UserRole.STUDENT
        )
        self.accountant = User.objects.create_user(
            username='ACC001',
            email='accountant@school.edu',
            password=self.password,
            first_name='Mary',
            last_name='Major',
            user_type=UserRole.ACCOUNTANT
        )
        self.librarian = User.objects.create_user(
            username='LIB001',
            email='librarian@school.edu',
            password=self.password,
            first_name='Book',
            last_name='Keeper',
            user_type=UserRole.LIBRARIAN
        )
        self.parent = User.objects.create_user(
            username='PAR001',
            email='parent@school.edu',
            password=self.password,
            first_name='Parent',
            last_name='Guardian',
            user_type=UserRole.PARENT
        )
        self.staff_user = User.objects.create_user(
            username='STF001',
            email='staff@school.edu',
            password=self.password,
            first_name='Support',
            last_name='Staff',
            user_type=UserRole.STAFF
        )

    def test_user_properties_and_roles(self):
        """Verify role properties on custom User model"""
        self.assertTrue(self.superadmin.is_superadmin)
        self.assertTrue(self.superadmin.is_staff)
        
        self.assertTrue(self.teacher.is_teacher)
        self.assertFalse(self.teacher.is_superadmin)
        self.assertFalse(self.teacher.is_student)
        
        self.assertTrue(self.student.is_student)
        self.assertTrue(self.accountant.is_accountant)
        self.assertTrue(self.librarian.is_librarian)
        self.assertTrue(self.parent.is_parent)
        self.assertTrue(self.staff_user.is_support_staff)

    def test_login_flow_with_email(self):
        """Verify login using email identifier"""
        response = self.client.post(reverse('accounts:login'), {
            'login_id': 'teacher@school.edu',
            'password': self.password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].email, 'teacher@school.edu')

    def test_login_flow_with_user_id(self):
        """Verify login using custom User ID (username)"""
        response = self.client.post(reverse('accounts:login'), {
            'login_id': 'TCH_MATH',
            'password': self.password,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'TCH_MATH')

    def test_manual_user_creation_and_login_flow(self):
        """Verify administrator can manually create a user with custom User ID & Password and user can login"""
        self.client.login(email='superadmin@school.edu', password=self.password)
        create_url = reverse('accounts:user_create')
        
        new_user_data = {
            'username': 'CUSTOM_TEACHER_99',
            'email': 'newteacher99@school.edu',
            'first_name': 'Robert',
            'last_name': 'Brown',
            'user_type': UserRole.TEACHER,
            'password': 'AssignedPassword123!',
            'confirm_password': 'AssignedPassword123!',
            'phone_number': '+1555123456',
            'gender': 'MALE',
            'is_active': 'on',
        }
        response = self.client.post(create_url, new_user_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify user exists in database
        new_user = User.objects.filter(username='CUSTOM_TEACHER_99').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.email, 'newteacher99@school.edu')
        self.assertEqual(new_user.user_type, UserRole.TEACHER)
        self.assertTrue(new_user.check_password('AssignedPassword123!'))

        # Logout admin and login as the newly created user using User ID
        self.client.logout()
        login_response = self.client.post(reverse('accounts:login'), {
            'login_id': 'CUSTOM_TEACHER_99',
            'password': 'AssignedPassword123!',
        }, follow=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.context['user'].is_authenticated)
        self.assertEqual(login_response.context['user'].username, 'CUSTOM_TEACHER_99')

    def test_parent_user_creation_with_linked_children(self):
        """Verify admin can create a Parent user and automatically link student wards"""
        from students.models import Student
        from parents.models import ParentProfile, ParentStudent

        # Create a test student model
        student1 = Student.objects.create(
            student_id='STU-2026-9901',
            admission_number='ADM-9901',
            first_name='David',
            last_name='Miller',
            gender='MALE',
            date_of_birth='2012-05-15',
            admission_date='2026-01-10',
            residential_address='123 Maple Street',
            emergency_contact_name='Robert Miller',
            emergency_contact_phone='555-0199',
            emergency_contact_relation='Father'
        )

        self.client.login(email='superadmin@school.edu', password=self.password)
        create_url = reverse('accounts:user_create')

        response = self.client.post(create_url, {
            'username': 'PAR_MILLER_01',
            'email': 'robert.miller@family.edu',
            'password': 'ParentSecurePass2026!',
            'confirm_password': 'ParentSecurePass2026!',
            'first_name': 'Robert',
            'last_name': 'Miller',
            'user_type': UserRole.PARENT,
            'phone_number': '555-0199',
            'gender': 'MALE',
            'is_active': 'on',
            'linked_children': [str(student1.id)],
            'relationship_type': 'FATHER',
            'is_primary_contact': 'on',
            'can_pickup_child': 'on'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        created_user = User.objects.filter(username='PAR_MILLER_01').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.user_type, UserRole.PARENT)
        
        # Verify ParentProfile created
        parent_profile = ParentProfile.objects.filter(user=created_user).first()
        self.assertIsNotNone(parent_profile)
        self.assertEqual(parent_profile.first_name, 'Robert')

        # Verify ParentStudent link created
        link = ParentStudent.objects.filter(parent=parent_profile, student=student1).first()
        self.assertIsNotNone(link)
        self.assertEqual(link.relationship_type, 'FATHER')
        self.assertTrue(link.is_primary_contact)
        self.assertTrue(link.can_pickup_child)

    def test_admin_password_reset_flow(self):
        """Verify admin can manually reassign password to an existing user"""
        self.client.login(email='superadmin@school.edu', password=self.password)
        reset_url = reverse('accounts:user_reset_password', kwargs={'pk': self.student.pk})

        response = self.client.post(reset_url, {
            'new_password': 'BrandNewPassword2026!',
            'confirm_password': 'BrandNewPassword2026!',
            'must_change_password': 'on',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify password changed
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('BrandNewPassword2026!'))
        self.assertTrue(self.student.must_change_password)

        # Verify user can login with new password
        self.client.logout()
        login_response = self.client.post(reverse('accounts:login'), {
            'login_id': 'STU2026_01',
            'password': 'BrandNewPassword2026!',
        }, follow=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.context['user'].is_authenticated)

    def test_toggle_active_status(self):
        """Verify administrator can deactivate and reactivate a user account"""
        self.client.login(email='superadmin@school.edu', password=self.password)
        toggle_url = reverse('accounts:user_toggle_active', kwargs={'pk': self.student.pk})

        # Deactivate
        self.client.post(toggle_url)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

        # Deactivated user cannot login
        self.client.logout()
        login_response = self.client.post(reverse('accounts:login'), {
            'login_id': 'student@school.edu',
            'password': self.password,
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "deactivated")

        # Reactivate
        self.client.login(email='superadmin@school.edu', password=self.password)
        self.client.post(toggle_url)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_user_list_view_and_permissions(self):
        """Verify user list is accessible to admin and denied to student"""
        # SuperAdmin allowed
        self.client.login(email='superadmin@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Management")

        # Student denied
        self.client.login(email='student@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_router_redirection(self):
        """Verify dashboard router dispatches user to appropriate role dashboard"""
        # Teacher Login
        self.client.login(email='teacher@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:dashboard_router'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:teacher_dashboard'))

        # Student Login
        self.client.login(email='student@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:dashboard_router'), follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:student_dashboard'))

    def test_all_role_dashboards_rendering(self):
        """Verify each persona can successfully load their dedicated dashboard view"""
        dashboards = [
            ('superadmin@school.edu', 'accounts:admin_dashboard'),
            ('principal@school.edu', 'accounts:principal_dashboard'),
            ('teacher@school.edu', 'accounts:teacher_dashboard'),
            ('accountant@school.edu', 'accounts:accountant_dashboard'),
            ('librarian@school.edu', 'accounts:librarian_dashboard'),
            ('student@school.edu', 'accounts:student_dashboard'),
            ('parent@school.edu', 'accounts:parent_dashboard'),
            ('staff@school.edu', 'accounts:staff_dashboard'),
        ]
        for email, url_name in dashboards:
            self.client.login(email=email, password=self.password)
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200, f"Dashboard {url_name} failed for {email}")

    def test_rbac_permission_denial(self):
        """Verify that Teacher cannot access Admin dashboard directly"""
        self.client.login(email='teacher@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_logout_flow(self):
        """Verify logout flushes session and redirects to login"""
        self.client.login(email='teacher@school.edu', password=self.password)
        response = self.client.get(reverse('accounts:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)

    def test_demo_fastfill_all_roles(self):
        """Verify all fastfill demo personas authenticate with Password@123"""
        demo_logins = [
            'admin@school.edu',
            'principal@school.edu',
            'teacher@school.edu',
            'accountant@school.edu',
            'student@school.edu',
            'parent@school.edu',
        ]
        for email in demo_logins:
            u = User.objects.filter(email=email).first()
            if not u:
                u = User.objects.create_user(email=email, password='Password@123')
            else:
                u.set_password('Password@123')
                u.save()
            
            self.client.logout()
            resp = self.client.post(reverse('accounts:login'), {
                'login_id': email,
                'password': 'Password@123',
            }, follow=True)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.context['user'].is_authenticated)
            self.assertEqual(resp.context['user'].email, email)

