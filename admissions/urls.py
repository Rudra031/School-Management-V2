from django.urls import path
from admissions import views

app_name = 'admissions'

urlpatterns = [
    path('', views.AdmissionsPipelineView.as_view(), name='pipeline'),
    path('quick/', views.QuickAdmissionView.as_view(), name='quick_admission'),
    path('full/', views.FullAdmissionView.as_view(), name='full_admission'),
    path('success/<str:app_num>/', views.AdmissionSuccessView.as_view(), name='admission_success'),
    path('<uuid:pk>/', views.AdmissionsApplicationDetailView.as_view(), name='detail'),
    path('<uuid:pk>/convert/', views.AdmissionsConvertStudentView.as_view(), name='convert_student'),
    path('<uuid:pk>/print/', views.AdmissionsPrintView.as_view(), name='print_admission'),
    path('student/<uuid:pk>/print/', views.StudentAdmissionPrintView.as_view(), name='print_student_admission'),
]
