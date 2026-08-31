from django.urls import path
from leave import views

app_name = 'leave'

urlpatterns = [
    path('', views.LeaveRequestListView.as_view(), name='list'),
    path('apply/', views.LeaveRequestCreateView.as_view(), name='apply'),
    path('<uuid:pk>/review/', views.LeaveReviewActionView.as_view(), name='review'),
]
