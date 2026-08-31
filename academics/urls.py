from django.urls import path
from academics import views

app_name = 'academics'

urlpatterns = [
    path('', views.AcademicOverviewView.as_view(), name='overview'),
    
    # Academic Years
    path('years/', views.AcademicYearListView.as_view(), name='year_list'),
    path('years/create/', views.AcademicYearCreateView.as_view(), name='year_create'),
    path('years/<uuid:pk>/edit/', views.AcademicYearUpdateView.as_view(), name='year_edit'),
    path('years/<uuid:pk>/set-active/', views.AcademicYearSetActiveView.as_view(), name='year_set_active'),
    
    # Classes (Add, Edit, Remove)
    path('classes/', views.ClassSectionManageView.as_view(), name='class_manage'),
    path('classes/create/', views.ClassCreateView.as_view(), name='class_create'),
    path('classes/<uuid:pk>/edit/', views.ClassUpdateView.as_view(), name='class_edit'),
    path('classes/<uuid:pk>/delete/', views.ClassDeleteView.as_view(), name='class_delete'),
    
    # Sections (Add, Edit, Remove)
    path('sections/create/', views.SectionCreateView.as_view(), name='section_create'),
    path('sections/<uuid:pk>/edit/', views.SectionUpdateView.as_view(), name='section_edit'),
    path('sections/<uuid:pk>/delete/', views.SectionDeleteView.as_view(), name='section_delete'),
    
    # Subjects (Add, Edit, Remove)
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<uuid:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_edit'),
    path('subjects/<uuid:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    
    # Teacher Allocations
    path('allocations/', views.TeacherAllocationView.as_view(), name='allocation_list'),
    path('allocations/create/', views.TeacherAllocationCreateView.as_view(), name='allocation_create'),
]
