from django.urls import path
from website import views

app_name = 'website'

urlpatterns = [
    # Public Virtual Pages
    path('', views.PublicHomeView.as_view(), name='home'),
    path('about/', views.PublicAboutView.as_view(), name='about'),
    path('academics/', views.PublicAcademicsView.as_view(), name='academics'),
    path('admissions/', views.PublicAdmissionsView.as_view(), name='admissions'),
    path('admissions/apply/', views.PublicAdmissionApplyView.as_view(), name='public_apply'),
    path('apply/', views.PublicAdmissionApplyView.as_view(), name='public_apply_shortcut'),
    path('admissions/success/<str:app_num>/', views.PublicAdmissionSuccessView.as_view(), name='public_apply_success'),
    path('admissions/track/', views.PublicAdmissionTrackView.as_view(), name='public_apply_track'),
    path('faculty/', views.PublicFacultyView.as_view(), name='faculty'),
    path('campus-life/', views.PublicCampusLifeView.as_view(), name='campus_life'),
    path('news-events/', views.PublicNewsEventsView.as_view(), name='news_events'),
    path('news/<slug:slug>/', views.PublicNewsDetailView.as_view(), name='news_detail'),
    path('testimonials/', views.PublicTestimonialsView.as_view(), name='testimonials'),
    path('contact/', views.PublicContactView.as_view(), name='contact'),

    # Admin No-Code Visual Studio Customizer
    path('customizer/', views.WebsiteCustomizerStudioView.as_view(), name='customizer_studio'),
    path('api/save-draft/', views.WebsiteCustomizerSaveDraftAPI.as_view(), name='api_save_draft'),
    path('api/publish/', views.WebsiteCustomizerPublishAPI.as_view(), name='api_publish'),
    
    # Admin CMS Content Studio
    path('cms/', views.WebsiteCMSDashboardView.as_view(), name='cms_dashboard'),
]
