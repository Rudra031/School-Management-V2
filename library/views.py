from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

from library.models import BookCategory, Book, BookCirculation
from library.forms import BookCategoryForm, BookForm, BookIssueForm
from core.permissions import LibrarianRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class BookCatalogListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'LIBRARIAN', 'TEACHER', 'STUDENT', 'PARENT']
    model = Book
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    paginate_by = 24

    def get_queryset(self):
        qs = Book.objects.filter(is_deleted=False).select_related('category')
        search = self.request.GET.get('search', '').strip()
        category_id = self.request.GET.get('category')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(isbn__icontains=search)
            )
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = BookCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class BookCreateView(LibrarianRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'library/book_form.html'
    success_url = reverse_lazy('library:catalog')

    def form_valid(self, form):
        messages.success(self.request, f"Book '{form.cleaned_data['title']}' cataloged.")
        return super().form_valid(form)


class BookCirculationListView(LibrarianRequiredMixin, ListView):
    model = BookCirculation
    template_name = 'library/circulation_list.html'
    context_object_name = 'loans'
    paginate_by = 25

    def get_queryset(self):
        status = self.request.GET.get('status', '')
        qs = BookCirculation.objects.filter(is_deleted=False).select_related('book', 'user', 'issued_by')
        if status == 'OVERDUE':
            qs = qs.filter(status=BookCirculation.Status.BORROWED, due_date__lt=timezone.now().date())
        elif status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_status'] = self.request.GET.get('status', '')
        context['active_loans_count'] = BookCirculation.objects.filter(status=BookCirculation.Status.BORROWED).count()
        context['overdue_loans_count'] = BookCirculation.objects.filter(
            status=BookCirculation.Status.BORROWED, due_date__lt=timezone.now().date()
        ).count()
        return context


class BookIssueView(LibrarianRequiredMixin, CreateView):
    model = BookCirculation
    form_class = BookIssueForm
    template_name = 'library/book_issue.html'
    success_url = reverse_lazy('library:circulation_list')

    @transaction.atomic
    def form_valid(self, form):
        loan = form.save(commit=False)
        book = loan.book
        if book.available_copies <= 0:
            messages.error(self.request, "Cannot issue: No copies available.")
            return self.form_invalid(form)

        book.available_copies -= 1
        book.save()

        loan.issued_by = self.request.user
        loan.status = BookCirculation.Status.BORROWED
        loan.save()

        messages.success(self.request, f"Book '{book.title}' issued to {loan.user.email} (Due: {loan.due_date}).")
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Library',
            model_name='BookCirculation',
            object_id=str(loan.id),
            object_repr=f"Issued {book.title} to {loan.user.email}"
        )
        return redirect('library:circulation_list')


class BookReturnView(LibrarianRequiredMixin, View):
    """
    Process returned book and calculate late fees ($1/day).
    """
    @transaction.atomic
    def post(self, request, pk):
        loan = get_object_or_404(BookCirculation, pk=pk)
        if loan.status != BookCirculation.Status.BORROWED:
            messages.warning(request, "This book loan is already closed.")
            return redirect('library:circulation_list')

        today = timezone.now().date()
        loan.return_date = today
        loan.status = BookCirculation.Status.RETURNED

        # Calculate late fine ($1.00 per overdue day)
        if today > loan.due_date:
            overdue_days = (today - loan.due_date).days
            loan.fine_amount = Decimal(str(overdue_days * 1.00))

        loan.save()

        # Increment available copies
        loan.book.available_copies += 1
        loan.book.save()

        if loan.fine_amount > 0:
            messages.warning(request, f"Book returned with ${loan.fine_amount} overdue fine applied.")
        else:
            messages.success(request, f"Book '{loan.book.title}' successfully returned.")

        return redirect('library:circulation_list')
