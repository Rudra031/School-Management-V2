from django.urls import path
from assignments import views

app_name = 'assignments'

urlpatterns = [
    path('', views.AssignmentListView.as_view(), name='list'),
    path('create/', views.AssignmentCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.AssignmentDetailView.as_view(), name='detail'),
    path('<uuid:pk>/submit/', views.AssignmentSubmitView.as_view(), name='submit'),
    path('submissions/<uuid:pk>/grade/', views.AssignmentGradeSubmissionView.as_view(), name='grade_submission'),
]
