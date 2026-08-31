from datetime import timedelta
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from library.models import BookCategory, Book, BookCirculation
from accounts.models import User

class BookCategoryForm(forms.ModelForm):
    class Meta:
        model = BookCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['isbn', 'title', 'author', 'publisher', 'edition', 'category', 'total_copies', 'available_copies', 'shelf_location', 'price']
        widgets = {
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ISBN-13 or barcode'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'edition': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'total_copies': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_copies': forms.NumberInput(attrs={'class': 'form-control'}),
            'shelf_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Shelf A-4'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class BookIssueForm(forms.ModelForm):
    default_due = lambda: timezone.now().date() + timedelta(days=14)
    due_date = forms.DateField(
        initial=default_due,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Return Due Date (Default: 14 Days)'
    )

    class Meta:
        model = BookCirculation
        fields = ['book', 'user', 'due_date', 'remarks']
        widgets = {
            'book': forms.Select(attrs={'class': 'form-select'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_book(self):
        book = self.cleaned_data.get('book')
        if book and book.available_copies <= 0:
            raise forms.ValidationError(f"All copies of '{book.title}' are currently checked out.")
        return book
