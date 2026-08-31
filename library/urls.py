from django.urls import path
from library import views

app_name = 'library'

urlpatterns = [
    path('', views.BookCatalogListView.as_view(), name='catalog'),
    path('books/create/', views.BookCreateView.as_view(), name='book_create'),
    path('circulation/', views.BookCirculationListView.as_view(), name='circulation_list'),
    path('circulation/issue/', views.BookIssueView.as_view(), name='book_issue'),
    path('circulation/<uuid:pk>/return/', views.BookReturnView.as_view(), name='book_return'),
]
