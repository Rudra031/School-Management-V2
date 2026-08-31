from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('password/change/', views.UserPasswordChangeView.as_view(), name='change_password'),

    # User Management (Create, List, Edit, Reset Password, Toggle Active)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/reset-password/', views.UserPasswordResetByAdminView.as_view(), name='user_reset_password'),
    path('users/<int:pk>/toggle-active/', views.UserToggleActiveView.as_view(), name='user_toggle_active'),
    
    # Dashboard Router
    path('dashboard/', views.DashboardRouterView.as_view(), name='dashboard_router'),
    
    # Role-Specific Dashboards (Standard Paths)
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/principal/', views.PrincipalDashboardView.as_view(), name='principal_dashboard'),
    path('dashboard/teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/accountant/', views.AccountantDashboardView.as_view(), name='accountant_dashboard'),
    path('dashboard/librarian/', views.LibrarianDashboardView.as_view(), name='librarian_dashboard'),
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/parent/', views.ParentDashboardView.as_view(), name='parent_dashboard'),
    path('dashboard/staff/', views.StaffDashboardView.as_view(), name='staff_dashboard'),

    # Direct Compatibility Aliases
    path('admin-dashboard/', views.AdminDashboardView.as_view()),
    path('principal-dashboard/', views.PrincipalDashboardView.as_view()),
    path('teacher-dashboard/', views.TeacherDashboardView.as_view()),
    path('accountant-dashboard/', views.AccountantDashboardView.as_view()),
    path('librarian-dashboard/', views.LibrarianDashboardView.as_view()),
    path('student-dashboard/', views.StudentDashboardView.as_view()),
    path('parent-dashboard/', views.ParentDashboardView.as_view()),
    path('staff-dashboard/', views.StaffDashboardView.as_view()),
]
