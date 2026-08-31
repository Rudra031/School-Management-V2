from django.urls import path
from examinations import views

app_name = 'examinations'

urlpatterns = [
    path('', views.ExamScheduleListView.as_view(), name='schedule_list'),
    path('terms/', views.ExamTermListView.as_view(), name='term_list'),
    path('terms/create/', views.ExamTermCreateView.as_view(), name='term_create'),
    path('schedules/create/', views.ExamScheduleCreateView.as_view(), name='schedule_create'),
    path('marks-entry/', views.ExamMarksEntryGridView.as_view(), name='marks_entry'),
    path('admit-card/', views.ExamAdmitCardView.as_view(), name='admit_card'),
    path('tabulation/', views.ClassTabulationSheetView.as_view(), name='tabulation_sheet'),
    path('promotion/', views.AcademicPromotionView.as_view(), name='academic_promotion'),
    path('report-card/<uuid:pk>/', views.StudentReportCardView.as_view(), name='report_card'),
    path('report-card/<uuid:pk>/pdf/', views.StudentReportCardPDFDownloadView.as_view(), name='report_card_pdf'),
]
