from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from fees.models import FeeCategory, StudentFeeInvoice, StudentFeePayment
from expenses.models import ExpenseCategory, Expense

class ReportsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Principal', last_name='Leader'
        )
        self.accountant = User.objects.create_user(
            email='accountant@school.edu', password=self.password, first_name='Finance', last_name='Officer', user_type=UserRole.ACCOUNTANT
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.grade10 = ClassLevel.objects.create(name='Grade 10', numeric_level=10)
        self.sec_a = Section.objects.create(class_level=self.grade10, name='A')

        # Create students
        self.student1 = Student.objects.create(
            admission_number='ADM-R1', student_id='STU-R1', first_name='John', last_name='Doe',
            gender='MALE', date_of_birth='2010-01-01', admission_date=today,
            residential_address='100 Main St', emergency_contact_name='Mary', emergency_contact_phone='123', emergency_contact_relation='Mother'
        )
        StudentEnrollment.objects.create(
            student=self.student1, academic_year=self.year, section=self.sec_a, roll_number=1, is_current=True
        )

        # Create Income: Fee payment
        cat_fee = FeeCategory.objects.create(name='Tuition')
        inv = StudentFeeInvoice.objects.create(
            invoice_number='INV-REP-01',
            student_enrollment=self.student1.enrollments.first(),
            academic_year=self.year,
            title='Tuition Term 1',
            issue_date=today,
            due_date=today + timedelta(days=30),
            total_amount=Decimal('5000.00'),
            balance_amount=Decimal('5000.00')
        )
        StudentFeePayment.objects.create(
            invoice=inv, receipt_number='REC-REP-01', payment_date=today, amount_paid=Decimal('5000.00'), collected_by=self.accountant
        )

        # Create Outflow: Expense
        cat_exp = ExpenseCategory.objects.create(name='Operations')
        Expense.objects.create(
            voucher_number='EXP-REP-01', academic_year=self.year, category=cat_exp, title='Server Infrastructure',
            amount=Decimal('1500.00'), expense_date=today, approved_by=self.accountant
        )

    def test_executive_reports_hub_and_demographics(self):
        """Verify executive reports hub and student demographics generation"""
        self.client.login(email='admin@school.edu', password=self.password)
        resp_hub = self.client.get(reverse('reports:hub'))
        self.assertEqual(resp_hub.status_code, 200)
        self.assertEqual(resp_hub.context['total_students'], 1)

        resp_demo = self.client.get(reverse('reports:demographics'))
        self.assertEqual(resp_demo.status_code, 200)
        self.assertEqual(len(resp_demo.context['class_rows']), 1)
        self.assertEqual(resp_demo.context['class_rows'][0]['male'], 1)

    def test_financial_statement_pnl_report(self):
        """Verify institutional P&L income ($5000) vs expense ($1500) = net surplus ($3500)"""
        self.client.login(email='accountant@school.edu', password=self.password)
        resp_pnl = self.client.get(reverse('reports:financial'))
        self.assertEqual(resp_pnl.status_code, 200)
        self.assertEqual(resp_pnl.context['total_income'], Decimal('5000.00'))
        self.assertEqual(resp_pnl.context['total_expenses'], Decimal('1500.00'))
        self.assertEqual(resp_pnl.context['net_balance'], Decimal('3500.00'))
        self.assertTrue(resp_pnl.context['is_surplus'])
