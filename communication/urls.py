from django.urls import path
from communication import views

app_name = 'communication'

urlpatterns = [
    path('', views.NoticeBoardView.as_view(), name='notice_board'),
    path('notices/create/', views.NoticeCreateView.as_view(), name='notice_create'),
    path('notices/<uuid:pk>/', views.NoticeDetailView.as_view(), name='notice_detail'),
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/<uuid:pk>/read/', views.NotificationMarkReadView.as_view(), name='notification_read'),
]
