from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, UserRole
from documents.models import DocumentCategory, SchoolDocument

class DocumentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='Officer'
        )
        self.student = User.objects.create_user(
            email='student@school.edu', password=self.password, first_name='Student', last_name='User', user_type=UserRole.STUDENT
        )

        self.cat = DocumentCategory.objects.create(name='Circulars & Policies')
        dummy_file = SimpleUploadedFile("policy.pdf", b"Dummy PDF content", content_type="application/pdf")
        
        self.doc_public = SchoolDocument.objects.create(
            title='Campus Code of Conduct', category=self.cat, document_file=dummy_file,
            access_level=SchoolDocument.AccessLevel.PUBLIC, uploaded_by=self.admin
        )
        self.doc_admin = SchoolDocument.objects.create(
            title='Audit & Financial Audit Report', category=self.cat, document_file=dummy_file,
            access_level=SchoolDocument.AccessLevel.RESTRICTED_ADMIN, uploaded_by=self.admin
        )

    def test_document_repository_access_control(self):
        """Verify role-based document access control"""
        # Admin can view all documents
        self.client.login(email='admin@school.edu', password=self.password)
        resp_admin = self.client.get(reverse('documents:list'))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(len(resp_admin.context['documents']), 2)

        # Student can only view public documents
        self.client.login(email='student@school.edu', password=self.password)
        resp_student = self.client.get(reverse('documents:list'))
        self.assertEqual(resp_student.status_code, 200)
        self.assertEqual(len(resp_student.context['documents']), 1)
        self.assertEqual(resp_student.context['documents'][0].title, 'Campus Code of Conduct')

    def test_certificate_generation_and_print(self):
        """Verify Transfer Certificate generation, token resolution, and print view"""
        from students.models import Student, StudentEnrollment
        from academics.models import AcademicYear, ClassLevel, Section
        from documents.models import CertificateType, IssuedCertificate
        from django.utils import timezone
        import datetime

        year = AcademicYear.objects.create(name='2026-2027', start_date=datetime.date(2026, 4, 1), end_date=datetime.date(2027, 3, 31), is_current=True)
        class_10 = ClassLevel.objects.create(name='Class 10', numeric_level=10)
        sec_a = Section.objects.create(class_level=class_10, name='A')

        student = Student.objects.create(
            first_name='Aarav', last_name='Sharma', gender='MALE',
            date_of_birth=datetime.date(2010, 5, 15),
            admission_number='ADM-2026-99', student_id='STU-99',
            admission_date=datetime.date(2020, 4, 1),
            emergency_contact_name='Rajesh Sharma',
            emergency_contact_phone='+91 98765 43210',
            residential_address='Dwarka, New Delhi'
        )
        enroll = StudentEnrollment.objects.create(
            student=student, section=sec_a, academic_year=year, roll_number='12'
        )

        self.client.login(email='admin@school.edu', password=self.password)

        # 1. Generate Transfer Certificate via POST
        resp_post = self.client.post(reverse('documents:certificate_generate'), {
            'form_type': 'TC',
            'student': str(student.id),
            'academic_year': str(year.id),
            'book_number': 'B-01',
            'serial_number': '099',
            'issue_date': timezone.now().date(),
            'leaving_date': timezone.now().date(),
            'reason_for_leaving': 'Parent Relocation',
            'general_conduct': 'Exemplary',
            'dues_cleared': 'on',
            'total_working_days': 220,
            'total_present_days': 210,
            'last_class_passed': 'Class 10 (AISSE)',
            'qualified_for_promotion': 'on',
            'ncc_cadet_or_scout': 'Scout Guide',
            'games_played': 'Football Team Captain',
            'custom_remarks': 'Outstanding student'
        })
        self.assertEqual(resp_post.status_code, 302)

        tc = IssuedCertificate.objects.filter(student=student, certificate_type=CertificateType.TRANSFER_CERTIFICATE).first()
        self.assertIsNotNone(tc)
        self.assertTrue(tc.certificate_number.startswith('TC/'))
        self.assertIsNotNone(tc.verification_token)

        # 2. Test Print View
        resp_print = self.client.get(reverse('documents:certificate_print', kwargs={'pk': tc.pk}))
        self.assertEqual(resp_print.status_code, 200)
        self.assertContains(resp_print, 'Aarav Sharma')
        self.assertContains(resp_print, 'Transfer Certificate')

        # 3. Test Public Verification Portal (Unauthenticated via token)
        self.client.logout()
        resp_verify = self.client.get(reverse('documents:certificate_verify', kwargs={'token': tc.verification_token}))
        self.assertEqual(resp_verify.status_code, 200)
        self.assertTrue(resp_verify.context['is_verified'])
        self.assertContains(resp_verify, 'OFFICIALLY VERIFIED')
        self.assertContains(resp_verify, 'Aarav Sharma')

        # 3b. Test Public Verification via Admission Number lookup
        resp_verify_adm = self.client.get(reverse('documents:certificate_verify_search') + f"?cert_no={student.admission_number}")
        self.assertEqual(resp_verify_adm.status_code, 200)
        self.assertTrue(resp_verify_adm.context['is_verified'])
        self.assertContains(resp_verify_adm, 'Aarav Sharma')

        # 3c. Test Public Real-time API Verification endpoint
        resp_api = self.client.get(reverse('documents:api_verify_certificate') + f"?q={student.admission_number}")
        self.assertEqual(resp_api.status_code, 200)
        api_data = resp_api.json()
        self.assertTrue(api_data['found'])
        self.assertEqual(api_data['student_name'], 'Aarav Sharma')
        self.assertEqual(api_data['certificate_number'], tc.certificate_number)

        # 4. Test Revocation
        self.client.login(email='admin@school.edu', password=self.password)
        resp_revoke = self.client.post(reverse('documents:certificate_revoke', kwargs={'pk': tc.pk}), {
            'revocation_reason': 'Duplicate entry'
        })
        self.assertEqual(resp_revoke.status_code, 302)
        tc.refresh_from_db()
        self.assertTrue(tc.is_revoked)

        # 5. Public verification after revocation
        self.client.logout()
        resp_verify_rev = self.client.get(reverse('documents:certificate_verify', kwargs={'token': tc.verification_token}))
        self.assertEqual(resp_verify_rev.status_code, 200)
        self.assertTrue(resp_verify_rev.context['is_revoked'])

    def test_id_card_studio_and_batch_views(self):
        """Verify ID Card Studio, Single PVC print, and 8-per-A4 batch print views"""
        from students.models import Student, StudentEnrollment
        from staff.models import StaffMember, Designation
        from academics.models import AcademicYear, ClassLevel, Section, Department
        import datetime

        year = AcademicYear.objects.create(name='2026-2027', start_date=datetime.date(2026, 4, 1), end_date=datetime.date(2027, 3, 31), is_current=True)
        class_10 = ClassLevel.objects.create(name='Class 10', numeric_level=11)
        sec_a = Section.objects.create(class_level=class_10, name='A')

        student = Student.objects.create(
            first_name='Kavya', last_name='Patel', gender='FEMALE',
            date_of_birth=datetime.date(2011, 8, 20),
            admission_number='ADM-2026-101', student_id='STU-101',
            admission_date=datetime.date(2021, 4, 1),
            emergency_contact_phone='+91 98111 22233',
            residential_address='Janakpuri, New Delhi'
        )
        StudentEnrollment.objects.create(student=student, section=sec_a, academic_year=year, roll_number='05')

        dept_acad = Department.objects.create(name='Mathematics & Science', code='MTHSCI')
        desig_tgt = Designation.objects.create(title='Senior TGT Mathematics', department=dept_acad)

        staff_user = User.objects.create_user(
            email='teacher1@school.edu', password=self.password, first_name='Priya', last_name='Menon', user_type=UserRole.TEACHER
        )
        staff = StaffMember.objects.create(
            user=staff_user, first_name='Priya', last_name='Menon', gender='FEMALE',
            employee_id='EMP-2026-01', designation=desig_tgt, department=dept_acad,
            date_of_birth=datetime.date(1988, 3, 10), joining_date=datetime.date(2020, 1, 1),
            emergency_contact_phone='+91 98222 33344'
        )

        self.client.login(email='admin@school.edu', password=self.password)

        # 1. Studio Student View
        resp_studio = self.client.get(reverse('documents:id_card_studio') + '?mode=STUDENT')
        self.assertEqual(resp_studio.status_code, 200)
        self.assertContains(resp_studio, 'Student & Staff ID Card Designer')

        # 2. Studio Staff View
        resp_studio_staff = self.client.get(reverse('documents:id_card_studio') + '?mode=STAFF')
        self.assertEqual(resp_studio_staff.status_code, 200)

        # 3. Single PVC Print View (Student)
        resp_single_stu = self.client.get(reverse('documents:id_card_print_single', kwargs={'entity_type': 'student', 'entity_id': student.pk}))
        self.assertEqual(resp_single_stu.status_code, 200)
        self.assertContains(resp_single_stu, 'Kavya Patel')

        # 4. Single PVC Print View (Staff)
        resp_single_staff = self.client.get(reverse('documents:id_card_print_single', kwargs={'entity_type': 'staff', 'entity_id': staff.pk}))
        self.assertEqual(resp_single_staff.status_code, 200)
        self.assertContains(resp_single_staff, 'Priya Menon')

        # 5. Bulk 8-per-A4 Batch Print View
        resp_bulk = self.client.get(reverse('documents:id_card_bulk_print') + f'?mode=STUDENT&class_id={class_10.id}')
        self.assertEqual(resp_bulk.status_code, 200)
        self.assertContains(resp_bulk, 'Batch ID Card Print')
        self.assertContains(resp_bulk, 'Kavya Patel')

