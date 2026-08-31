from django.urls import path
from timetable import views

app_name = 'timetable'

urlpatterns = [
    path('', views.TimetableOverviewView.as_view(), name='overview'),
    path('entries/create/', views.TimetableEntryCreateView.as_view(), name='entry_create'),
    path('entries/<uuid:pk>/delete/', views.TimetableEntryDeleteView.as_view(), name='entry_delete'),
    path('slots/', views.TimeSlotListView.as_view(), name='slot_list'),
    path('slots/create/', views.TimeSlotCreateView.as_view(), name='slot_create'),
]
