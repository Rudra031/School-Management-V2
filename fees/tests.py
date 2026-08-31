from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from fees.models import FeeCategory, FeeStructure, StudentFeeInvoice, StudentFeePayment, FeeConcession, StudentConcession, FeeFineRule

class FeesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.accountant = User.objects.create_user(
            email='accountant@school.edu', password=self.password, first_name='Finance', last_name='Officer', user_type=UserRole.ACCOUNTANT
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.class10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.class10, name='A')

        self.student = Student.objects.create(
            admission_number='ADM-500', student_id='STU-500', first_name='Bruce', last_name='Wayne',
            gender='MALE', date_of_birth='2010-02-19', admission_date=today,
            residential_address='Wayne Manor', emergency_contact_name='Alfred', emergency_contact_phone='100', emergency_contact_relation='Butler'
        )
        self.enrollment = StudentEnrollment.objects.create(
            student=self.student, academic_year=self.year, section=self.sec_a, roll_number=1, is_current=True
        )

        self.category = FeeCategory.objects.create(name='Tuition Fee', category_type=FeeCategory.CategoryType.TUITION)
        self.concession = FeeConcession.objects.create(name='Sibling Discount', code='SIBLING20', concession_type=FeeConcession.ConcessionType.PERCENTAGE, discount_value=Decimal('20.00'))
        self.fine_rule = FeeFineRule.objects.create(name='Standard Late Fine', fine_type=FeeFineRule.FineType.PER_DAY, grace_period_days=5, fine_amount=Decimal('50.00'), max_fine_limit=Decimal('500.00'), academic_year=self.year)

    def test_invoice_creation_and_payment_settlement(self):
        """Verify fee invoice creation, partial payment, and full settlement"""
        invoice = StudentFeeInvoice.objects.create(
            invoice_number='INV-2026-0001',
            student_enrollment=self.enrollment,
            academic_year=self.year,
            title='Term 1 Tuition Fee',
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('1000.00'),
            balance_amount=Decimal('1000.00'),
            status=StudentFeeInvoice.Status.UNPAID
        )
        self.assertEqual(invoice.balance_amount, Decimal('1000.00'))
        self.assertEqual(invoice.status, StudentFeeInvoice.Status.UNPAID)

        # 1. Partial Payment of ₹400
        payment1 = StudentFeePayment.objects.create(
            invoice=invoice,
            receipt_number='REC-001',
            payment_date=timezone.now().date(),
            amount_paid=Decimal('400.00'),
            payment_method=StudentFeePayment.PaymentMethod.CASH,
            collected_by=self.accountant
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('400.00'))
        self.assertEqual(invoice.balance_amount, Decimal('600.00'))
        self.assertEqual(invoice.status, StudentFeeInvoice.Status.PARTIAL)

        # 2. Final Payment of ₹600 with UPI
        payment2 = StudentFeePayment.objects.create(
            invoice=invoice,
            receipt_number='REC-002',
            payment_date=timezone.now().date(),
            amount_paid=Decimal('600.00'),
            payment_method=StudentFeePayment.PaymentMethod.UPI,
            upi_utr_number='423589123456',
            collected_by=self.accountant
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('1000.00'))
        self.assertEqual(invoice.balance_amount, Decimal('0.00'))
        self.assertEqual(invoice.status, StudentFeeInvoice.Status.PAID)

    def test_fee_concession_and_fine_calculation(self):
        """Verify concession mapping and late fine computation"""
        StudentConcession.objects.create(student_enrollment=self.enrollment, concession=self.concession, academic_year=self.year)

        invoice = StudentFeeInvoice.objects.create(
            invoice_number='INV-2026-CONC',
            student_enrollment=self.enrollment,
            academic_year=self.year,
            title='Tuition Fee with Concession',
            issue_date=timezone.now().date() - timedelta(days=20),
            due_date=timezone.now().date() - timedelta(days=10),
            total_amount=Decimal('5000.00'),
            discount_amount=Decimal('1000.00'), # 20%
            balance_amount=Decimal('4000.00'),
            concession_applied=self.concession
        )
        self.assertEqual(invoice.net_payable, Decimal('4000.00'))
        self.assertTrue(invoice.is_overdue)
        self.assertEqual(invoice.overdue_days, 10)

        # Apply late fine rule: (10 - 5 grace days) * 50 = 250
        fine_applied = invoice.calculate_and_apply_fine(self.fine_rule)
        self.assertEqual(fine_applied, Decimal('250.00'))
        self.assertEqual(invoice.fine_amount, Decimal('250.00'))
        self.assertEqual(invoice.net_payable, Decimal('4250.00'))

    def test_pos_counter_and_views(self):
        """Verify POS collection counter and receipt print views"""
        invoice = StudentFeeInvoice.objects.create(
            invoice_number='INV-2026-POS',
            student_enrollment=self.enrollment,
            academic_year=self.year,
            title='Annual Fee',
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=30),
            total_amount=Decimal('1200.00'),
            balance_amount=Decimal('1200.00'),
        )
        self.client.login(email='accountant@school.edu', password=self.password)
        
        # POS search & render
        resp_pos = self.client.get(reverse('fees:pos_counter') + f'?q={self.student.admission_number}')
        self.assertEqual(resp_pos.status_code, 200)

        # POS payment submission
        resp_pay = self.client.post(reverse('fees:pos_counter'), {
            'invoice_id': invoice.id,
            'amount_paid': '1200.00',
            'payment_method': 'UPI',
            'upi_utr_number': '987654321012',
            'notes': 'Paid in full at POS counter'
        })
        self.assertEqual(resp_pay.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, StudentFeeInvoice.Status.PAID)

        # Defaulters View
        resp_def = self.client.get(reverse('fees:defaulters_list'))
        self.assertEqual(resp_def.status_code, 200)

