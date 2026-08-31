from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import Department, AcademicYear
from staff.models import StaffMember, Designation, SalaryStructure, PayrollPeriod, StaffSalarySlip

class StaffTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.admin = User.objects.create_superuser(
            email='admin@school.edu', password=self.password, first_name='Admin', last_name='User'
        )
        self.dept = Department.objects.create(name='Languages', code='LANG')
        self.desig = Designation.objects.create(title='English Teacher', department=self.dept, is_teaching_role=True)
        self.academic_year = AcademicYear.objects.create(
            name='2026-2027',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365),
            is_current=True
        )

    def test_staff_create_flow(self):
        """Verify staff creation view creates both User and StaffMember profiles"""
        self.client.login(email='admin@school.edu', password=self.password)
        response = self.client.post(reverse('staff:staff_create'), {
            'email': 'sarah@school.edu',
            'password': 'StaffPassword123!',
            'phone_number': '+1 (555) 333-4444',
            'employee_id': 'EMP-2026-0045',
            'designation': str(self.desig.id),
            'department': str(self.dept.id),
            'first_name': 'Sarah',
            'last_name': 'Connor',
            'gender': 'FEMALE',
            'date_of_birth': '1990-05-15',
            'qualification': 'M.A. English Literature',
            'experience_years': 5,
            'joining_date': '2026-01-10',
            'basic_salary': '4500.00',
            'contract_type': 'PERMANENT',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check StaffMember and User were created
        staff = StaffMember.objects.filter(employee_id='EMP-2026-0045').first()
        self.assertIsNotNone(staff)
        self.assertEqual(staff.full_name, 'Sarah Connor')
        self.assertEqual(staff.user.email, 'sarah@school.edu')
        self.assertEqual(staff.user.user_type, UserRole.TEACHER)

    def test_staff_export_csv_and_excel(self):
        """Verify staff export views return valid responses"""
        self.client.login(email='admin@school.edu', password=self.password)
        
        # CSV Export
        resp_csv = self.client.get(reverse('staff:staff_export') + '?format=csv')
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv['Content-Type'], 'text/csv')

        # Excel Export
        resp_excel = self.client.get(reverse('staff:staff_export') + '?format=excel')
        self.assertEqual(resp_excel.status_code, 200)

    def test_salary_structure_computation(self):
        """Verify Basic + Allowances - Deductions = Net Salary math"""
        user = User.objects.create_user(email='teacher@school.edu', password=self.password, user_type=UserRole.TEACHER)
        staff = StaffMember.objects.create(
            user=user,
            employee_id='EMP-101',
            designation=self.desig,
            department=self.dept,
            first_name='John',
            last_name='Doe',
            gender='MALE',
            joining_date='2026-01-01',
            basic_salary=Decimal('4000.00')
        )
        struct = SalaryStructure.objects.create(
            staff_member=staff,
            basic_salary=Decimal('4000.00'),
            house_rent_allowance=Decimal('600.00'),
            transport_allowance=Decimal('250.00'),
            medical_allowance=Decimal('150.00'),
            special_allowance=Decimal('200.00'),
            tax_deduction=Decimal('300.00'),
            provident_fund=Decimal('200.00'),
            insurance_deduction=Decimal('100.00'),
            other_deductions=Decimal('0.00')
        )
        self.assertEqual(struct.total_allowances, Decimal('1200.00'))
        self.assertEqual(struct.total_deductions, Decimal('600.00'))
        self.assertEqual(struct.gross_salary, Decimal('5200.00'))
        self.assertEqual(struct.net_salary, Decimal('4600.00'))

    def test_payroll_batch_generation_and_disbursement(self):
        """Verify batch generation of monthly payroll and salary slips"""
        self.client.login(email='admin@school.edu', password=self.password)
        
        # Create a test employee
        user = User.objects.create_user(email='staff2@school.edu', password=self.password, user_type=UserRole.TEACHER)
        staff = StaffMember.objects.create(
            user=user,
            employee_id='EMP-102',
            designation=self.desig,
            department=self.dept,
            first_name='Alice',
            last_name='Smith',
            gender='FEMALE',
            joining_date='2026-01-01',
            basic_salary=Decimal('5000.00')
        )
        SalaryStructure.objects.create(
            staff_member=staff,
            basic_salary=Decimal('5000.00'),
            house_rent_allowance=Decimal('800.00'),
            transport_allowance=Decimal('300.00'),
            medical_allowance=Decimal('200.00'),
            special_allowance=Decimal('100.00'),
            tax_deduction=Decimal('400.00'),
            provident_fund=Decimal('250.00'),
            insurance_deduction=Decimal('50.00')
        )

        # Trigger batch generation
        resp = self.client.post(reverse('staff:payroll_generate'), {
            'academic_year': str(self.academic_year.id),
            'month': 8,
            'year': 2026,
            'payment_date': '2026-08-31',
            'payment_method': 'BANK_TRANSFER',
            'notes': 'August 2026 payroll run'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Check PayrollPeriod and StaffSalarySlip
        period = PayrollPeriod.objects.filter(academic_year=self.academic_year, month=8, year=2026).first()
        self.assertIsNotNone(period)
        self.assertEqual(period.status, PayrollPeriod.Status.GENERATED)

        slip = StaffSalarySlip.objects.filter(payroll_period=period, staff_member=staff).first()
        self.assertIsNotNone(slip)
        self.assertEqual(slip.slip_number, 'PAY-2026-08-EMP-102')
        self.assertEqual(slip.basic_salary, Decimal('5000.00'))
        self.assertEqual(slip.gross_salary, Decimal('6400.00'))
        self.assertEqual(slip.total_deductions, Decimal('700.00'))
        self.assertEqual(slip.net_salary, Decimal('5700.00'))

        # Approve Payroll
        resp_app = self.client.post(reverse('staff:payroll_period_approve', kwargs={'pk': period.pk}), follow=True)
        self.assertEqual(resp_app.status_code, 200)
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriod.Status.APPROVED)

        # Disburse Payroll
        resp_dis = self.client.post(reverse('staff:payroll_period_disburse', kwargs={'pk': period.pk}), follow=True)
        self.assertEqual(resp_dis.status_code, 200)
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriod.Status.PAID)

        # Check Slip View & Print View
        resp_view = self.client.get(reverse('staff:salary_slip_detail', kwargs={'pk': slip.pk}))
        self.assertEqual(resp_view.status_code, 200)
        self.assertContains(resp_view, 'PAY-2026-08-EMP-102')

        resp_print = self.client.get(reverse('staff:salary_slip_print', kwargs={'pk': slip.pk}))
        self.assertEqual(resp_print.status_code, 200)
        self.assertContains(resp_print, 'Alice Smith')
