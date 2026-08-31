import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, TemplateView
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils import timezone

from expenses.models import ExpenseCategory, Expense
from expenses.forms import ExpenseCategoryForm, ExpenseForm
from academics.models import AcademicYear
from core.permissions import AccountantRequiredMixin, RoleRequiredMixin
from core.utils import log_audit, export_to_csv, export_to_excel
from core.models import AuditLog

class ExpenseOverviewView(AccountantRequiredMixin, TemplateView):
    """
    Operating Expenses & Cash Outflow Overview.
    """
    template_name = 'expenses/expense_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        qs = Expense.objects.filter(is_deleted=False)
        if academic_year:
            qs = qs.filter(academic_year=academic_year)

        total_expenses = qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        recent_expenses = qs.select_related('category', 'approved_by')[:10]

        # Category Breakdown
        category_breakdown = []
        for cat in ExpenseCategory.objects.all():
            cat_total = qs.filter(category=cat).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            if cat_total > 0:
                category_breakdown.append({
                    'category': cat,
                    'total': cat_total,
                    'percentage': round((cat_total / total_expenses * 100), 1) if total_expenses > 0 else 0
                })

        context['academic_year'] = academic_year
        context['total_expenses'] = total_expenses
        context['recent_expenses'] = recent_expenses
        context['category_breakdown'] = category_breakdown
        return context


class ExpenseListView(AccountantRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 25

    def get_queryset(self):
        qs = Expense.objects.filter(is_deleted=False).select_related('category', 'approved_by')
        search = self.request.GET.get('search', '').strip()
        category_id = self.request.GET.get('category')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(voucher_number__icontains=search) |
                Q(vendor_name__icontains=search)
            )
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class ExpenseCreateView(AccountantRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:list')

    def form_valid(self, form):
        exp = form.save(commit=False)
        exp.voucher_number = f"EXP-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        exp.approved_by = self.request.user
        exp.save()
        messages.success(self.request, f"Expense voucher '{exp.voucher_number}' (${exp.amount}) recorded.")
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Expenses',
            model_name='Expense',
            object_id=str(exp.id),
            object_repr=f"{exp.voucher_number} - {exp.title} (${exp.amount})"
        )
        return redirect('expenses:list')


class ExpenseExportView(AccountantRequiredMixin, View):
    def get(self, request):
        qs = Expense.objects.filter(is_deleted=False).select_related('category')
        fmt = request.GET.get('format', 'csv')
        filename = f"institutional_expenses_{timezone.now().strftime('%Y%m%d')}"

        headers = ['Voucher Number', 'Date', 'Expense Title', 'Category', 'Vendor', 'Payment Method', 'Amount ($)']
        rows = [
            [
                e.voucher_number,
                e.expense_date.strftime('%Y-%m-%d'),
                e.title,
                e.category.name if e.category else 'General',
                e.vendor_name,
                e.get_payment_method_display(),
                str(e.amount)
            ]
            for e in qs
        ]

        if fmt == 'excel':
            return export_to_excel(filename, headers, rows)
        return export_to_csv(filename, headers, rows)
