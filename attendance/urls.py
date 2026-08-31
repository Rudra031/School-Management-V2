from django.urls import path
from attendance import views

app_name = 'attendance'

urlpatterns = [
    path('', views.DailyAttendanceMarkingView.as_view(), name='mark'),
    path('monthly/', views.MonthlyAttendanceMatrixView.as_view(), name='monthly_matrix'),
    path('api/update-cell/', views.AttendanceCellUpdateAPIView.as_view(), name='api_update_cell'),
    path('report/', views.AttendanceReportView.as_view(), name='report'),
    path('staff/', views.StaffAttendanceListView.as_view(), name='staff_attendance'),
]
