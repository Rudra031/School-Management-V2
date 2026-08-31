from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from academics.models import AcademicYear
from expenses.models import ExpenseCategory, Expense

class ExpensesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.accountant = User.objects.create_user(
            email='accountant@school.edu', password=self.password, first_name='Finance', last_name='Officer', user_type=UserRole.ACCOUNTANT
        )

        today = timezone.now().date()
        self.year = AcademicYear.objects.create(name='2025-2026', start_date=today, end_date=today + timedelta(days=365), is_current=True)
        self.cat_util = ExpenseCategory.objects.create(name='Utilities & Maintenance')
        self.cat_supp = ExpenseCategory.objects.create(name='Office Supplies')

    def test_expense_creation_and_overview_aggregation(self):
        """Verify recording expenses, voucher generation, and accountant overview calculations"""
        exp1 = Expense.objects.create(
            voucher_number='EXP-2026-0001',
            academic_year=self.year,
            category=self.cat_util,
            title='Campus Electricity Bill',
            amount=Decimal('1200.00'),
            expense_date=timezone.now().date(),
            payment_method=Expense.PaymentMethod.BANK_TRANSFER,
            approved_by=self.accountant
        )
        exp2 = Expense.objects.create(
            voucher_number='EXP-2026-0002',
            academic_year=self.year,
            category=self.cat_supp,
            title='Classroom Stationery & Markers',
            amount=Decimal('350.00'),
            expense_date=timezone.now().date(),
            payment_method=Expense.PaymentMethod.CASH,
            approved_by=self.accountant
        )

        self.client.login(email='accountant@school.edu', password=self.password)
        resp = self.client.get(reverse('expenses:overview'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_expenses'], Decimal('1550.00'))
        self.assertEqual(len(resp.context['category_breakdown']), 2)

        resp_list = self.client.get(reverse('expenses:list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(len(resp_list.context['expenses']), 2)
