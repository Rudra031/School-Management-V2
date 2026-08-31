from django.urls import path
from parents import views

app_name = 'parents'

urlpatterns = [
    path('', views.ParentListView.as_view(), name='parent_list'),
    path('create/', views.ParentCreateView.as_view(), name='parent_create'),
    path('<uuid:pk>/', views.ParentDetailView.as_view(), name='parent_detail'),
    path('<uuid:pk>/link-student/', views.ParentLinkStudentView.as_view(), name='link_student'),
    path('<uuid:pk>/unlink-student/<uuid:student_id>/', views.ParentUnlinkStudentView.as_view(), name='unlink_student'),
    path('switch-child/<uuid:child_id>/', views.ParentSwitchChildView.as_view(), name='switch_child'),
    path('apply-leave/', views.ParentWardLeaveCreateView.as_view(), name='ward_leave'),
    path('ward-timetable/', views.ParentChildTimetableView.as_view(), name='ward_timetable'),
]

