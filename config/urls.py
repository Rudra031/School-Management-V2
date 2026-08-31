from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect

# Custom Error Handlers
def custom_bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)

def custom_permission_denied(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def custom_page_not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def custom_server_error(request):
    return render(request, 'errors/500.html', status=500)

handler400 = custom_bad_request
handler403 = custom_permission_denied
handler404 = custom_page_not_found
handler500 = custom_server_error

from website import views as website_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Root renders the Public School Landing Page
    path('', website_views.PublicHomeView.as_view(), name='root'),
    
    # Phase 1: Core Persona & Auth
    path('accounts/', include('accounts.urls', namespace='accounts')),
    
    # Phase 2: Core Academics, Staff, Students & Parents
    path('academics/', include('academics.urls', namespace='academics')),
    path('staff/', include('staff.urls', namespace='staff')),
    path('students/', include('students.urls', namespace='students')),
    path('parents/', include('parents.urls', namespace='parents')),
    
    # Phase 3: Academic Operations
    path('timetable/', include('timetable.urls', namespace='timetable')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('examinations/', include('examinations.urls', namespace='examinations')),
    path('assignments/', include('assignments.urls', namespace='assignments')),

    # Phase 4: Operations, Finance & Administration
    path('fees/', include('fees.urls', namespace='fees')),
    path('library/', include('library.urls', namespace='library')),
    path('admissions/', include('admissions.urls', namespace='admissions')),
    path('leave/', include('leave.urls', namespace='leave')),
    path('documents/', include('documents.urls', namespace='documents')),

    # Phase 5: Communication, Inventory, Expenses & Reports Hub
    path('communication/', include('communication.urls', namespace='communication')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('expenses/', include('expenses.urls', namespace='expenses')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('core/', include('core.urls', namespace='core')),
    path('settings/', include('core.urls', namespace='core_settings')),

    # Modern 3D Public School Website & Visual Customizer
    path('portal/', include('website.urls', namespace='website')),
    path('website/', include('website.urls', namespace='website_customizer')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
