from django.urls import path
from documents import views

app_name = 'documents'

urlpatterns = [
    path('', views.DocumentRepositoryListView.as_view(), name='list'),
    path('upload/', views.DocumentUploadView.as_view(), name='upload'),
    path('<uuid:pk>/delete/', views.DocumentDeleteView.as_view(), name='delete'),
    
    # Digital Certificate Studio Routes
    path('certificates/', views.CertificateStudioView.as_view(), name='certificate_studio'),
    path('certificates/generate/', views.CertificateGenerateView.as_view(), name='certificate_generate'),
    path('certificates/<uuid:pk>/print/', views.CertificatePrintView.as_view(), name='certificate_print'),
    path('certificates/<uuid:pk>/pdf/', views.CertificatePDFDownloadView.as_view(), name='certificate_pdf'),
    path('certificates/<uuid:pk>/revoke/', views.CertificateRevokeView.as_view(), name='certificate_revoke'),
    path('certificates/verify/', views.PublicCertificateVerifyView.as_view(), name='certificate_verify_search'),
    path('certificates/verify/<uuid:token>/', views.PublicCertificateVerifyView.as_view(), name='certificate_verify'),
    path('api/verify-certificate/', views.PublicCertificateVerifyAPIView.as_view(), name='api_verify_certificate'),
    
    # ID Card Designer & Bulk Generator Routes
    path('id-cards/', views.IDCardStudioView.as_view(), name='id_card_studio'),
    path('id-cards/bulk-print/', views.BulkIDCardBatchPrintView.as_view(), name='id_card_bulk_print'),
    path('id-cards/<str:entity_type>/<uuid:entity_id>/print/', views.SingleIDCardPrintView.as_view(), name='id_card_print_single'),
]
