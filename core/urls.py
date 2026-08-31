from django.urls import path
from core.views import (
    SchoolSettingsView,
    SystemBackupDownloadView,
    SystemRestoreUploadView,
    SystemFactoryResetView,
    LicenseLockoutView,
    LicenseActivateView,
    LicenseStatusAPIView,
)

app_name = 'core'

urlpatterns = [
    path('', SchoolSettingsView.as_view(), name='index'),
    path('settings/', SchoolSettingsView.as_view(), name='settings'),
    path('backup/', SystemBackupDownloadView.as_view(), name='backup_download_direct'),
    path('restore/', SystemRestoreUploadView.as_view(), name='restore_upload_direct'),
    path('factory-reset/', SystemFactoryResetView.as_view(), name='factory_reset_direct'),
    path('settings/backup/', SystemBackupDownloadView.as_view(), name='backup_download'),
    path('settings/restore/', SystemRestoreUploadView.as_view(), name='restore_upload'),
    path('settings/factory-reset/', SystemFactoryResetView.as_view(), name='factory_reset'),
    
    # Software Licensing & 7-Day Trial Routes
    path('license/lockout/', LicenseLockoutView.as_view(), name='license_lockout'),
    path('license/activate/', LicenseActivateView.as_view(), name='license_activate'),
    path('license/status/', LicenseStatusAPIView.as_view(), name='license_status_api'),
]

