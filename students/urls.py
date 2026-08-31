from django.urls import path
from students import views

app_name = 'students'

urlpatterns = [
    path('', views.StudentListView.as_view(), name='student_list'),
    path('register/', views.StudentRegistrationView.as_view(), name='student_register'),
    path('export/', views.StudentExportView.as_view(), name='student_export'),
    path('promote/', views.StudentPromotionView.as_view(), name='student_promote'),
    path('<uuid:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('<uuid:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('<uuid:pk>/health/', views.StudentHealthView.as_view(), name='student_health'),
    path('<uuid:pk>/health/incident/', views.StudentMedicalIncidentCreateView.as_view(), name='incident_create'),
    path('my-timetable/', views.StudentMyTimetableView.as_view(), name='my_timetable'),
    path('my-attendance/', views.StudentMyAttendanceView.as_view(), name='my_attendance'),
    path('id-card/<uuid:pk>/', views.StudentIDCardView.as_view(), name='id_card'),
]

