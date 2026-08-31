from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from library.models import BookCategory, Book, BookCirculation

class LibraryTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'Pass12345!'
        self.librarian = User.objects.create_user(
            email='librarian@school.edu', password=self.password, first_name='Library', last_name='Staff', user_type=UserRole.LIBRARIAN
        )
        self.student = User.objects.create_user(
            email='student@school.edu', password=self.password, first_name='Student', last_name='Reader', user_type=UserRole.STUDENT
        )

        self.cat = BookCategory.objects.create(name='Science Fiction')
        self.book = Book.objects.create(
            isbn='978-0441172719', title='Dune', author='Frank Herbert',
            category=self.cat, total_copies=3, available_copies=3, shelf_location='Shelf SF-1'
        )

    def test_book_issue_and_inventory_decrement(self):
        """Verify issuing book decreases available copies and sets due date"""
        self.client.login(email='librarian@school.edu', password=self.password)
        due = (timezone.now().date() + timedelta(days=14)).strftime('%Y-%m-%d')
        
        response = self.client.post(reverse('library:book_issue'), {
            'book': str(self.book.id),
            'user': str(self.student.id),
            'due_date': due,
            'remarks': 'Mint condition',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 2)

        loan = BookCirculation.objects.filter(book=self.book, user=self.student).first()
        self.assertIsNotNone(loan)
        self.assertEqual(loan.status, BookCirculation.Status.BORROWED)

    def test_book_return_and_overdue_fine_calculation(self):
        """Verify returning overdue book applies daily fines ($1/day) and increments available copies"""
        # Create a loan that was due 5 days ago
        past_due = timezone.now().date() - timedelta(days=5)
        loan = BookCirculation.objects.create(
            book=self.book,
            user=self.student,
            borrow_date=timezone.now().date() - timedelta(days=19),
            due_date=past_due,
            status=BookCirculation.Status.BORROWED,
            issued_by=self.librarian
        )
        self.book.available_copies = 2
        self.book.save()

        self.client.login(email='librarian@school.edu', password=self.password)
        response = self.client.post(reverse('library:book_return', kwargs={'pk': loan.pk}), follow=True)
        self.assertEqual(response.status_code, 200)

        loan.refresh_from_db()
        self.assertEqual(loan.status, BookCirculation.Status.RETURNED)
        self.assertEqual(loan.fine_amount, Decimal('5.00')) # 5 days * $1.00

        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 3)
