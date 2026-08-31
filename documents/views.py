from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, CreateView, DeleteView
from django.contrib import messages
from django.db.models import Q
from django.db import models

from documents.models import DocumentCategory, SchoolDocument
from documents.forms import SchoolDocumentForm
from core.permissions import RoleRequiredMixin, SchoolAdminRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class DocumentRepositoryListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT', 'PARENT']
    model = SchoolDocument
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 25

    def get_queryset(self):
        qs = SchoolDocument.objects.filter(is_deleted=False).select_related('category', 'uploaded_by', 'student', 'staff_member')
        
        # Role-based access control filters
        user = self.request.user
        if not (user.is_superadmin or user.is_school_admin or user.is_principal):
            if user.is_teacher or user.is_accountant or user.is_librarian or user.is_support_staff:
                qs = qs.filter(access_level__in=[
                    SchoolDocument.AccessLevel.PUBLIC,
                    SchoolDocument.AccessLevel.STAFF_ONLY,
                    SchoolDocument.AccessLevel.PARENT_ACCESSIBLE
                ])
            elif user.is_student:
                student = getattr(user, 'student_profile', None)
                student_q = Q(student=student) if student else Q(pk__in=[])
                qs = qs.filter(
                    Q(access_level=SchoolDocument.AccessLevel.PUBLIC) |
                    Q(access_level=SchoolDocument.AccessLevel.PARENT_ACCESSIBLE) |
                    student_q
                )
            elif user.is_parent:
                parent = getattr(user, 'parent_profile', None)
                children = parent.children if parent else []
                children_q = Q(student__in=children) if children else Q(pk__in=[])
                qs = qs.filter(
                    Q(access_level=SchoolDocument.AccessLevel.PUBLIC) |
                    Q(access_level=SchoolDocument.AccessLevel.PARENT_ACCESSIBLE) |
                    children_q
                )

        search = self.request.GET.get('search', '').strip()
        category_id = self.request.GET.get('category')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class DocumentUploadView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN']
    model = SchoolDocument
    form_class = SchoolDocumentForm
    template_name = 'documents/document_form.html'
    success_url = reverse_lazy('documents:list')

    def form_valid(self, form):
        doc = form.save(commit=False)
        doc.uploaded_by = self.request.user
        doc.save()
        messages.success(self.request, f"Document '{doc.title}' uploaded to repository.")
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Documents',
            model_name='SchoolDocument',
            object_id=str(doc.id),
            object_repr=doc.title
        )
        return redirect('documents:list')


class DocumentDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = SchoolDocument
    success_url = reverse_lazy('documents:list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Document removed from repository.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# DIGITAL CERTIFICATE STUDIO VIEWS
# ==========================================

from django.views.generic import TemplateView, DetailView
from django.utils import timezone
from datetime import timedelta
from students.models import Student, StudentEnrollment
from staff.models import StaffMember
from academics.models import ClassLevel, Section, AcademicYear
from documents.models import (
    CertificateType, CertificateTemplate, IssuedCertificate,
    IDCardConfiguration, IDCardOrientation, IDCardTheme, IssuedIDCard
)
from documents.forms import (
    TransferCertificateGenerateForm, GenericCertificateGenerateForm, IDCardDesignConfigForm
)


class CertificateStudioView(RoleRequiredMixin, TemplateView):
    """
    Split-pane Digital Certificate Studio with live A4 preview, KPI strip, and issuance ledger.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']
    template_name = 'documents/certificate_studio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Top KPI Metrics
        all_certs = IssuedCertificate.objects.filter(is_deleted=False)
        context['kpi_total_issued'] = all_certs.filter(status=IssuedCertificate.Status.ISSUED).count()
        context['kpi_tc_issued'] = all_certs.filter(certificate_type=CertificateType.TRANSFER_CERTIFICATE, status=IssuedCertificate.Status.ISSUED).count()
        context['kpi_bonafide_issued'] = all_certs.filter(certificate_type=CertificateType.BONAFIDE_CERTIFICATE, status=IssuedCertificate.Status.ISSUED).count()
        context['kpi_revoked'] = all_certs.filter(is_revoked=True).count()
        
        # Forms
        context['tc_form'] = TransferCertificateGenerateForm(initial={
            'issue_date': timezone.now().date(),
            'leaving_date': timezone.now().date(),
            'book_number': 'B-01',
            'serial_number': f"{(all_certs.count() + 1):03d}"
        })
        context['generic_form'] = GenericCertificateGenerateForm(initial={
            'issue_date': timezone.now().date(),
            'certificate_type': CertificateType.CHARACTER_CERTIFICATE
        })
        
        # Search & Filtered Certificates Ledger
        search_query = self.request.GET.get('q', '').strip()
        type_filter = self.request.GET.get('type', '')
        
        qs = all_certs.select_related('student', 'academic_year', 'student_enrollment__section__class_level').order_by('-issue_date', '-created_at')
        if search_query:
            qs = qs.filter(
                Q(certificate_number__icontains=search_query) |
                Q(student__first_name__icontains=search_query) |
                Q(student__last_name__icontains=search_query) |
                Q(student__admission_number__icontains=search_query)
            )
        if type_filter:
            qs = qs.filter(certificate_type=type_filter)
            
        context['certificates'] = qs[:50]
        context['certificate_types'] = CertificateType.choices
        context['selected_type'] = type_filter
        context['search_query'] = search_query
        
        # Preview candidate
        preview_id = self.request.GET.get('preview')
        if preview_id:
            context['preview_cert'] = IssuedCertificate.objects.filter(pk=preview_id, is_deleted=False).first()
        else:
            context['preview_cert'] = qs.first()
            
        return context


class CertificateGenerateView(RoleRequiredMixin, View):
    """
    Processes creation of Transfer Certificate or Generic Certificate.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']

    def post(self, request, *args, **kwargs):
        cert_type = request.POST.get('form_type', 'TC')
        
        if cert_type == 'TC':
            form = TransferCertificateGenerateForm(request.POST)
            if form.is_valid():
                cert = form.save(commit=False)
                cert.certificate_type = CertificateType.TRANSFER_CERTIFICATE
                year_str = timezone.now().strftime('%Y')
                cert.certificate_number = f"TC/{year_str}/{cert.serial_number or '001'}"
                cert.issued_by = request.user
                
                # Link active enrollment if student selected
                if cert.student:
                    active_enroll = cert.student.enrollments.filter(is_current=True).first()
                    if active_enroll:
                        cert.student_enrollment = active_enroll
                        if not cert.academic_year:
                            cert.academic_year = active_enroll.academic_year
                
                cert.save()
                messages.success(request, f"Transfer Certificate {cert.certificate_number} generated successfully for {cert.student.full_name}.")
                log_audit(request, action=AuditLog.Action.CREATE, module='Documents', model_name='IssuedCertificate', object_id=str(cert.id), object_repr=cert.certificate_number)
                return redirect(reverse_lazy('documents:certificate_studio') + f'?preview={cert.id}')
            else:
                messages.error(request, f"Error generating Transfer Certificate: {form.errors.as_text()}")
        else:
            form = GenericCertificateGenerateForm(request.POST)
            if form.is_valid():
                cert = form.save(commit=False)
                prefix_map = {
                    CertificateType.CHARACTER_CERTIFICATE: 'CC',
                    CertificateType.BONAFIDE_CERTIFICATE: 'BON',
                    CertificateType.FEE_CLEARANCE: 'FC',
                    CertificateType.MIGRATION: 'MIG',
                    CertificateType.CUSTOM: 'CERT',
                }
                pref = prefix_map.get(cert.certificate_type, 'DOC')
                year_str = timezone.now().strftime('%Y')
                seq = IssuedCertificate.objects.filter(certificate_type=cert.certificate_type).count() + 1
                cert.certificate_number = f"{pref}/{year_str}/{seq:03d}"
                cert.issued_by = request.user
                
                if cert.student:
                    active_enroll = cert.student.enrollments.filter(is_current=True).first()
                    if active_enroll:
                        cert.student_enrollment = active_enroll
                        if not cert.academic_year:
                            cert.academic_year = active_enroll.academic_year
                
                cert.save()
                messages.success(request, f"Certificate {cert.certificate_number} generated successfully for {cert.student.full_name}.")
                log_audit(request, action=AuditLog.Action.CREATE, module='Documents', model_name='IssuedCertificate', object_id=str(cert.id), object_repr=cert.certificate_number)
                return redirect(reverse_lazy('documents:certificate_studio') + f'?preview={cert.id}')
            else:
                messages.error(request, f"Error generating Certificate: {form.errors.as_text()}")
                
        return redirect('documents:certificate_studio')


class CertificatePrintView(RoleRequiredMixin, DetailView):
    """
    Official A4 Printable Parchment Certificate view with guilloche border, seal watermark, and QR code.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']
    model = IssuedCertificate
    template_name = 'documents/certificate_print.html'
    context_object_name = 'cert'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cert = self.get_object()
        enroll = cert.student_enrollment or cert.student.enrollments.filter(is_current=True).first()
        context['enrollment'] = enroll
        
        # Build absolute URL for public verification QR
        host = self.request.get_host()
        protocol = 'https' if self.request.is_secure() else 'http'
        context['verify_url'] = f"{protocol}://{host}/documents/certificates/verify/{cert.verification_token}/"
        return context


class CertificatePDFDownloadView(RoleRequiredMixin, View):
    """
    Generates and streams official statutory vector PDF Transfer Certificate / Character / Bonafide certificate.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']

    def get(self, request, pk, *args, **kwargs):
        cert = get_object_or_404(IssuedCertificate, pk=pk, is_deleted=False)
        from core.pdf_generator import generate_transfer_certificate_pdf
        from django.http import HttpResponse

        pdf_buffer = generate_transfer_certificate_pdf(cert)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename_clean = cert.certificate_number.replace('/', '_').replace(' ', '_')
        response['Content-Disposition'] = f'inline; filename="Certificate_{filename_clean}.pdf"'
        return response


def find_certificate_record(query, token=None):
    """
    Intelligent multi-criteria lookup engine to locate authentic TC/CC certificates.
    Supports token, certificate number, admission number, student ID, and variations.
    """
    from documents.models import IssuedCertificate
    if token:
        try:
            return IssuedCertificate.objects.filter(
                verification_token=token, is_deleted=False
            ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').first()
        except Exception:
            pass

    if not query:
        return None

    query = str(query).strip()

    # 1. Exact match on certificate_number
    cert = IssuedCertificate.objects.filter(
        certificate_number__iexact=query, is_deleted=False
    ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').first()
    if cert:
        return cert

    # 2. Normalized separators (e.g. TC-2026-001 -> TC/2026/001, CC 2026 001 -> CC/2026/001)
    normalized = query.replace('-', '/').replace(' ', '/').replace('\\', '/')
    cert = IssuedCertificate.objects.filter(
        certificate_number__iexact=normalized, is_deleted=False
    ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').first()
    if cert:
        return cert

    # 3. Match on student admission number
    cert = IssuedCertificate.objects.filter(
        student__admission_number__iexact=query, is_deleted=False
    ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').order_by('-issue_date').first()
    if cert:
        return cert

    # 4. Match on student ID
    cert = IssuedCertificate.objects.filter(
        student__student_id__iexact=query, is_deleted=False
    ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').order_by('-issue_date').first()
    if cert:
        return cert

    # 5. Fuzzy contains search on certificate number or student admission number or name
    cert = IssuedCertificate.objects.filter(
        models.Q(certificate_number__icontains=query) |
        models.Q(student__admission_number__icontains=query) |
        models.Q(student__first_name__icontains=query) |
        models.Q(student__last_name__icontains=query),
        is_deleted=False
    ).select_related('student', 'academic_year', 'student_enrollment__section__class_level').order_by('-issue_date').first()

    return cert


class PublicCertificateVerifyView(View):
    """
    Public Authentication Portal: Verifies authenticity of certificates via QR scan or token/number lookup.
    """
    def get(self, request, token=None, *args, **kwargs):
        search_query = request.GET.get('cert_no', '').strip() or request.GET.get('q', '').strip()
        cert = find_certificate_record(search_query, token=token)
        
        context = {
            'cert': cert,
            'search_query': search_query,
            'token': token,
            'is_verified': cert is not None and not cert.is_revoked,
            'is_revoked': cert is not None and cert.is_revoked,
        }
        return render(request, 'documents/certificate_verify.html', context)


class PublicCertificateVerifyAPIView(View):
    """
    Public Real-Time JSON API for TC/CC Certificate Verification.
    Used by landing page search modals to authenticate certificates without page reload.
    """
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'found': False, 'message': 'Please provide a certificate or admission number.'})

        cert = find_certificate_record(query)
        if not cert:
            return JsonResponse({
                'found': False,
                'query': query,
                'message': f"No authentic certificate record found matching '{query}'. Please verify the Admission No. or Certificate No."
            })

        enroll = cert.student_enrollment or cert.student.enrollments.filter(is_current=True).first()
        class_name = enroll.section.full_name if enroll and enroll.section else (cert.last_class_passed or 'Class X')

        return JsonResponse({
            'found': True,
            'certificate_number': cert.certificate_number,
            'certificate_type': cert.get_certificate_type_display(),
            'student_name': cert.student.full_name,
            'admission_number': cert.student.admission_number,
            'guardian_name': cert.student.emergency_contact_name or 'Parent/Guardian',
            'date_of_birth': cert.student.date_of_birth.strftime('%d %B %Y') if cert.student.date_of_birth else 'N/A',
            'class_name': class_name,
            'issue_date': cert.issue_date.strftime('%d %B %Y') if cert.issue_date else 'N/A',
            'leaving_date': cert.leaving_date.strftime('%d %B %Y') if cert.leaving_date else 'N/A',
            'general_conduct': cert.general_conduct or 'Exemplary',
            'reason_for_leaving': cert.reason_for_leaving or 'Completed Academic Course',
            'dues_cleared': cert.dues_cleared,
            'is_revoked': cert.is_revoked,
            'revocation_reason': cert.revocation_reason if cert.is_revoked else '',
            'verification_token': str(cert.verification_token),
            'verify_url': reverse('documents:certificate_verify', kwargs={'token': cert.verification_token}),
            'school_name': 'Horizon Premier Public School',
            'affiliation_no': '2430089',
            'school_code': '15614',
        })


class CertificateRevokeView(SchoolAdminRequiredMixin, View):
    """
    Revokes an issued certificate with an official reason.
    """
    def post(self, request, pk, *args, **kwargs):
        cert = get_object_or_404(IssuedCertificate, pk=pk)
        reason = request.POST.get('revocation_reason', 'Revoked by school administration')
        cert.is_revoked = True
        cert.status = IssuedCertificate.Status.REVOKED
        cert.revocation_reason = reason
        cert.save()
        messages.warning(request, f"Certificate {cert.certificate_number} has been REVOKED.")
        log_audit(request, action=AuditLog.Action.UPDATE, module='Documents', model_name='IssuedCertificate', object_id=str(cert.id), object_repr=f"REVOKED: {cert.certificate_number}")
        return redirect('documents:certificate_studio')


# ==========================================
# ID CARD DESIGNER & BULK GENERATOR VIEWS
# ==========================================

from academics.models import Department

class IDCardStudioView(RoleRequiredMixin, TemplateView):
    """
    Interactive Student & Staff ID Card Studio with theme switchers, live dual-sided preview, and bulk generator.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']
    template_name = 'documents/id_card_studio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter parameters
        mode = self.request.GET.get('mode', 'STUDENT') # 'STUDENT' or 'STAFF'
        class_id = self.request.GET.get('class_id')
        section_id = self.request.GET.get('section_id')
        dept = self.request.GET.get('department')
        search = self.request.GET.get('q', '').strip()
        
        context['mode'] = mode
        context['class_levels'] = ClassLevel.objects.filter(is_deleted=False).prefetch_related('sections')
        context['sections'] = Section.objects.filter(is_deleted=False)
        context['departments'] = Department.objects.filter(is_deleted=False)
        
        # KPI metrics
        total_students = Student.objects.filter(is_deleted=False, status=Student.Status.ACTIVE).count()
        total_staff = StaffMember.objects.filter(is_deleted=False, status=StaffMember.Status.ACTIVE).count()
        context['kpi_total_students'] = total_students
        context['kpi_total_staff'] = total_staff
        context['kpi_total_cards'] = total_students + total_staff
        
        # Get or create default config
        config = IDCardConfiguration.objects.filter(is_default=True).first()
        if not config:
            config = IDCardConfiguration.objects.first()
        if not config:
            config = IDCardConfiguration.objects.create(
                name='Default Academic Preset',
                orientation=IDCardOrientation.PORTRAIT,
                theme=IDCardTheme.NAVY_GOLD,
                primary_color='#1E1B4B',
                accent_color='#D4AF37',
                is_default=True
            )
        context['config'] = config
        context['config_form'] = IDCardDesignConfigForm(instance=config)
        context['orientations'] = IDCardOrientation.choices
        context['themes'] = IDCardTheme.choices
        
        # Query entities for selection list
        if mode == 'STUDENT':
            students_qs = Student.objects.filter(is_deleted=False, status=Student.Status.ACTIVE).select_related('user')
            if class_id:
                students_qs = students_qs.filter(enrollments__section__class_level_id=class_id, enrollments__is_current=True)
            if section_id:
                students_qs = students_qs.filter(enrollments__section_id=section_id, enrollments__is_current=True)
            if search:
                students_qs = students_qs.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(admission_number__icontains=search)
                )
            context['records'] = students_qs.distinct()[:50]
            context['sample_holder'] = students_qs.first() or Student.objects.filter(is_deleted=False).first()
        else:
            staff_qs = StaffMember.objects.filter(is_deleted=False, status=StaffMember.Status.ACTIVE).select_related('user', 'designation', 'department')
            if dept:
                staff_qs = staff_qs.filter(department_id=dept)
            if search:
                staff_qs = staff_qs.filter(
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(employee_id__icontains=search)
                )
            context['records'] = staff_qs[:50]
            context['sample_holder'] = staff_qs.first() or StaffMember.objects.filter(is_deleted=False).first()
            
        context['selected_class_id'] = class_id
        context['selected_section_id'] = section_id
        context['selected_department'] = dept
        context['search_query'] = search
        
        return context


class BulkIDCardBatchPrintView(RoleRequiredMixin, View):
    """
    8-Cards-per-A4 sheet printable batch layout for selected class, section, or department.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER']

    def get(self, request, *args, **kwargs):
        mode = request.GET.get('mode', 'STUDENT')
        class_id = request.GET.get('class_id')
        section_id = request.GET.get('section_id')
        dept = request.GET.get('department')
        orientation = request.GET.get('orientation', 'PORTRAIT')
        theme = request.GET.get('theme', 'NAVY_GOLD')
        
        config = IDCardConfiguration.objects.filter(is_default=True).first()
        
        cards = []
        year = AcademicYear.objects.filter(is_current=True).first()
        valid_until = timezone.now().date() + timedelta(days=365)
        
        if mode == 'STUDENT':
            students_qs = Student.objects.filter(is_deleted=False, status=Student.Status.ACTIVE).select_related('user').prefetch_related('enrollments__section__class_level')
            if class_id:
                students_qs = students_qs.filter(enrollments__section__class_level_id=class_id, enrollments__is_current=True)
            if section_id:
                students_qs = students_qs.filter(enrollments__section_id=section_id, enrollments__is_current=True)
                
            for stu in students_qs.distinct():
                active_enroll = stu.enrollments.filter(is_current=True).first()
                cards.append({
                    'type': 'STUDENT',
                    'entity': stu,
                    'enrollment': active_enroll,
                    'name': stu.full_name,
                    'code': stu.admission_number,
                    'sub_title': active_enroll.section.full_name if active_enroll and active_enroll.section else 'Student',
                    'blood_group': stu.blood_group or 'O+',
                    'dob': stu.date_of_birth,
                    'emergency_phone': stu.emergency_contact_phone or '+91 98765 43210',
                    'address': stu.residential_address or 'Dwarka, New Delhi',
                    'photo': stu.photo.url if stu.photo else None,
                    'valid_until': valid_until,
                    'route_no': 'Route #12 (Dwarka Expy)',
                })
        else:
            staff_qs = StaffMember.objects.filter(is_deleted=False, status=StaffMember.Status.ACTIVE).select_related('user', 'designation', 'department')
            if dept:
                staff_qs = staff_qs.filter(department_id=dept)
                
            for stf in staff_qs:
                cards.append({
                    'type': 'STAFF',
                    'entity': stf,
                    'name': stf.full_name,
                    'code': stf.employee_id,
                    'sub_title': f"{stf.designation.title if stf.designation else 'Staff'}",
                    'blood_group': stf.blood_group or 'B+',
                    'dob': stf.date_of_birth,
                    'emergency_phone': stf.emergency_contact_phone or '+91 98765 43210',
                    'address': getattr(stf, 'residential_address', 'New Delhi - Staff Quarters'),
                    'photo': stf.photo.url if stf.photo else None,
                    'valid_until': valid_until,
                    'route_no': 'Faculty Transport #04',
                })
                
        context = {
            'cards': cards,
            'mode': mode,
            'orientation': orientation,
            'theme': theme,
            'config': config,
            'academic_year': year,
        }
        return render(request, 'documents/id_card_print_batch.html', context)


class SingleIDCardPrintView(RoleRequiredMixin, View):
    """
    Single CR80 PVC badge printable layout (Front + Back side).
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']

    def get(self, request, entity_type, entity_id, *args, **kwargs):
        orientation = request.GET.get('orientation', 'PORTRAIT')
        theme = request.GET.get('theme', 'NAVY_GOLD')
        year = AcademicYear.objects.filter(is_current=True).first()
        valid_until = timezone.now().date() + timedelta(days=365)
        
        card_data = None
        if entity_type == 'student':
            stu = get_object_or_404(Student, pk=entity_id)
            active_enroll = stu.enrollments.filter(is_current=True).first()
            card_data = {
                'type': 'STUDENT',
                'entity': stu,
                'enrollment': active_enroll,
                'name': stu.full_name,
                'code': stu.admission_number,
                'sub_title': active_enroll.section.full_name if active_enroll and active_enroll.section else 'Student',
                'blood_group': stu.blood_group or 'O+',
                'dob': stu.date_of_birth,
                'emergency_phone': stu.emergency_contact_phone or '+91 98765 43210',
                'address': stu.residential_address or 'Dwarka, New Delhi',
                'photo': stu.photo.url if stu.photo else None,
                'valid_until': valid_until,
                'route_no': 'Route #12 (Dwarka)',
            }
        else:
            stf = get_object_or_404(StaffMember, pk=entity_id)
            card_data = {
                'type': 'STAFF',
                'entity': stf,
                'name': stf.full_name,
                'code': stf.employee_id,
                'sub_title': f"{stf.designation.title if stf.designation else 'Staff'}",
                'blood_group': stf.blood_group or 'B+',
                'dob': stf.date_of_birth,
                'emergency_phone': stf.emergency_contact_phone or '+91 98765 43210',
                'address': getattr(stf, 'residential_address', 'New Delhi - Staff Quarters'),
                'photo': stf.photo.url if getattr(stf, 'photo', None) else None,
                'valid_until': valid_until,
                'route_no': 'Faculty Transit #04',
            }
            
        context = {
            'card': card_data,
            'orientation': orientation,
            'theme': theme,
            'academic_year': year,
        }
        return render(request, 'documents/id_card_print_single.html', context)


