import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class BookCategory(BaseModel):
    """
    Library Book Categories (e.g. Science, Literature, History, Computer Science).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Book Category')
        verbose_name_plural = _('Book Categories')

    def __str__(self):
        return self.name


class Book(BaseModel):
    """
    Library Catalog Book master record.
    """
    isbn = models.CharField(max_length=50, blank=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    author = models.CharField(max_length=200, db_index=True)
    publisher = models.CharField(max_length=150, blank=True)
    edition = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(BookCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    shelf_location = models.CharField(max_length=50, blank=True, help_text=_('e.g. Aisle 3, Rack B'))
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['title']
        verbose_name = _('Library Book')
        verbose_name_plural = _('Library Books')

    def __str__(self):
        return f"{self.title} by {self.author} ({self.available_copies}/{self.total_copies} Avail)"

    @property
    def is_available(self):
        return self.available_copies > 0


class BookCirculation(BaseModel):
    """
    Book Borrowing & Circulation record.
    """
    class Status(models.TextChoices):
        BORROWED = 'BORROWED', _('Active Borrow')
        RETURNED = 'RETURNED', _('Returned')
        OVERDUE = 'OVERDUE', _('Overdue')
        LOST = 'LOST', _('Reported Lost')

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrows')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowed_books')
    borrow_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BORROWED)
    fine_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    fine_paid = models.BooleanField(default=False)
    
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_book_loans'
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-borrow_date', '-created_at']
        verbose_name = _('Book Circulation')
        verbose_name_plural = _('Book Circulations')

    def __str__(self):
        return f"{self.book.title} -> {self.user.email} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        if self.status == self.Status.BORROWED and timezone.now().date() > self.due_date:
            return True
        return False
