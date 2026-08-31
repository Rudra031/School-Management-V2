import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView, FormView
from django.db import transaction, models
from django.contrib import messages
from django.utils import timezone

from admissions.models import AdmissionsApplication
from admissions.forms import (
    AdmissionsApplicationForm,
    QuickAdmissionForm,
    AdmissionsReviewForm,
    AdmissionsConvertStudentForm
)
from students.models import Student, StudentEnrollment
from academics.models import AcademicYear, ClassLevel, Section
from core.permissions import SchoolAdminRequiredMixin, RoleRequiredMixin
from core.utils import log_audit
from core.models import AuditLog


class AdmissionsPipelineView(SchoolAdminRequiredMixin, ListView):
    """
    Student Admission & Enrollment Control Center / Applications Directory.
    """
    model = AdmissionsApplication
    template_name = 'admissions/pipeline.html'
    context_object_name = 'applications'
    paginate_by = 25

    def get_queryset(self):
        qs = AdmissionsApplication.objects.filter(is_deleted=False).select_related('academic_year', 'applying_for_class')
        status = self.request.GET.get('status')
        class_id = self.request.GET.get('class_level')
        search = self.request.GET.get('search', '').strip()
        if status:
            qs = qs.filter(status=status)
        if class_id:
            qs = qs.filter(applying_for_class_id=class_id)
        if search:
            qs = qs.filter(
                models.Q(application_number__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(parent_name__icontains=search) |
                models.Q(parent_phone__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_apps = AdmissionsApplication.objects.filter(is_deleted=False)
        today = timezone.now().date()
        total_count = all_apps.count()
        today_inquiries = all_apps.filter(created_at__date=today).count()
        quick_mode_count = all_apps.filter(application_number__startswith='ADM-QUICK').count()
        full_mode_count = all_apps.exclude(application_number__startswith='ADM-QUICK').count()
        
        submitted_count = all_apps.filter(status=AdmissionsApplication.Stage.SUBMITTED).count()
        review_count = all_apps.filter(status=AdmissionsApplication.Stage.UNDER_REVIEW).count()
        shortlist_count = all_apps.filter(status=AdmissionsApplication.Stage.SHORTLISTED).count()
        accepted_count = all_apps.filter(status=AdmissionsApplication.Stage.ACCEPTED).count()
        enrolled_count = all_apps.filter(status=AdmissionsApplication.Stage.ENROLLED).count()
        rejected_count = all_apps.filter(status=AdmissionsApplication.Stage.REJECTED).count()
        
        conversion_rate = round((enrolled_count / total_count * 100), 1) if total_count > 0 else 0.0

        context.update({
            'total_count': total_count,
            'today_inquiries': today_inquiries,
            'quick_mode_count': quick_mode_count,
            'full_mode_count': full_mode_count,
            'submitted_count': submitted_count,
            'review_count': review_count,
            'shortlist_count': shortlist_count,
            'accepted_count': accepted_count,
            'enrolled_count': enrolled_count,
            'rejected_count': rejected_count,
            'conversion_rate': conversion_rate,
            'stages': AdmissionsApplication.Stage.choices,
            'class_levels': ClassLevel.objects.filter(is_deleted=False).order_by('numeric_level'),
            'selected_status': self.request.GET.get('status', ''),
            'selected_class': self.request.GET.get('class_level', ''),
            'search_query': self.request.GET.get('search', ''),
        })
        return context


class QuickAdmissionView(SchoolAdminRequiredMixin, FormView):
    """
    Mode 1: Rapid 1-Page Student Admission & Instant Enrollment.
    """
    template_name = 'admissions/quick_admission.html'
    form_class = QuickAdmissionForm
    success_url = reverse_lazy('admissions:pipeline')

    def form_valid(self, form):
        action = self.request.POST.get('action', 'enroll')
        app = form.save(commit=False)
        app.application_number = f"ADM-QUICK-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:5].upper()}"
        
        if action == 'draft':
            app.status = AdmissionsApplication.Stage.SUBMITTED
            app.notes = "Saved as quick draft admission."
            app.save()
            messages.info(self.request, f"Quick admission draft '{app.application_number}' saved.")
            return redirect('admissions:pipeline')

        # Instant Enroll Flow
        app.status = AdmissionsApplication.Stage.ENROLLED
        app.reviewed_by = self.request.user
        app.save()

        # Create Student record
        assigned_section = form.cleaned_data.get('section') or form.cleaned_data['applying_for_class'].sections.first()
        student_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
        admission_number = f"ADM-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"

        student = Student.objects.create(
            first_name=app.first_name,
            last_name=app.last_name,
            gender=app.gender,
            date_of_birth=app.date_of_birth,
            student_id=student_id,
            admission_number=admission_number,
            admission_date=timezone.now().date(),
            status=Student.Status.ACTIVE,
            residential_address=app.residential_address,
            emergency_contact_name=app.parent_name,
            emergency_contact_phone=app.parent_phone,
            emergency_contact_relation='Guardian',
            previous_school_name=app.previous_school
        )

        if assigned_section:
            StudentEnrollment.objects.create(
                student=student,
                academic_year=app.academic_year,
                section=assigned_section,
                roll_number=StudentEnrollment.objects.filter(section=assigned_section, academic_year=app.academic_year).count() + 1
            )

        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Admissions',
            model_name='Student',
            object_id=str(student.id),
            object_repr=f"Quick Admission: {student.full_name} ({student.admission_number})"
        )

        if action == 'enroll_and_continue':
            messages.success(
                self.request,
                f"Student '{student.full_name}' fast-enrolled! Complete the full profile dossier, document uploads, and transport allocation below."
            )
            return redirect(f"{reverse('admissions:full_admission')}?app_id={app.id}")

        messages.success(
            self.request,
            f"Student '{student.full_name}' successfully enrolled with Admission No: {student.admission_number}!"
        )
        return redirect('admissions:admission_success', app_num=app.application_number)


class FullAdmissionView(SchoolAdminRequiredMixin, TemplateView):
    """
    Mode 2: Advanced 10-Step Full Admission Wizard.
    Supports continuing from a Quick Admission application.
    """
    template_name = 'admissions/full_admission.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_id = self.request.GET.get('app_id')
        existing_app = None
        existing_student = None
        if app_id:
            existing_app = AdmissionsApplication.objects.filter(id=app_id, is_deleted=False).select_related('applying_for_class', 'academic_year').first()
            if existing_app:
                existing_student = Student.objects.filter(first_name=existing_app.first_name, last_name=existing_app.last_name).order_by('-created_at').first()

        context.update({
            'academic_years': AcademicYear.objects.all(),
            'class_levels': ClassLevel.objects.filter(is_deleted=False).order_by('numeric_level'),
            'sections': Section.objects.filter(is_deleted=False),
            'generated_app_no': existing_app.application_number if existing_app else f"APP-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:5].upper()}",
            'today': timezone.now().date(),
            'existing_app': existing_app,
            'existing_student': existing_student,
        })
        return context

    def post(self, request, *args, **kwargs):
        existing_app_id = request.POST.get('existing_app_id')

        # 1. Student Info
        first_name = request.POST.get('first_name', '').strip() or 'Student'
        last_name = request.POST.get('last_name', '').strip()
        gender = request.POST.get('gender', 'MALE')
        dob = request.POST.get('date_of_birth') or '2012-05-15'
        blood_group = request.POST.get('blood_group', '')
        religion = request.POST.get('religion', '')
        nationality = request.POST.get('nationality', 'Indian')

        # 2. Family Info
        father_name = request.POST.get('father_name', '')
        father_phone = request.POST.get('father_phone', '')
        mother_name = request.POST.get('mother_name', '')
        mother_phone = request.POST.get('mother_phone', '')
        parent_name = request.POST.get('parent_name') or father_name or mother_name or 'Parent/Guardian'
        parent_phone = request.POST.get('parent_phone') or father_phone or mother_phone or '+91-9876543210'
        parent_email = request.POST.get('parent_email', 'parent@school.edu')

        # 3. Address & Emergency Info
        address = request.POST.get('residential_address', 'Main Campus Area')
        emergency_contact_name = request.POST.get('emergency_contact_name') or parent_name
        emergency_contact_phone = request.POST.get('emergency_contact_phone') or parent_phone

        # 4. Previous School & TC
        prev_school = request.POST.get('previous_school_name', '')
        prev_board = request.POST.get('previous_board', '')
        last_grade = request.POST.get('last_grade', '')
        tc_number = request.POST.get('tc_number', '')

        # 5. Academic Info
        class_id = request.POST.get('applying_for_class')
        section_id = request.POST.get('section')
        year_id = request.POST.get('academic_year')

        class_obj = ClassLevel.objects.filter(id=class_id).first() if class_id else ClassLevel.objects.first()
        section_obj = Section.objects.filter(id=section_id).first() if section_id else (class_obj.sections.first() if class_obj else None)
        year_obj = AcademicYear.objects.filter(id=year_id).first() if year_id else AcademicYear.objects.filter(is_current=True).first()

        with transaction.atomic():
            if existing_app_id:
                app = AdmissionsApplication.objects.filter(id=existing_app_id).first()
            else:
                app = None

            if app:
                # Update existing application
                app.first_name = first_name
                app.last_name = last_name
                app.gender = gender
                app.date_of_birth = dob
                app.parent_name = parent_name
                app.parent_phone = parent_phone
                app.parent_email = parent_email
                app.residential_address = address
                if class_obj:
                    app.applying_for_class = class_obj
                if year_obj:
                    app.academic_year = year_obj
                if prev_school:
                    app.previous_school = f"{prev_school} ({prev_board}) - Last Grade: {last_grade}, TC: {tc_number}"
                app.status = AdmissionsApplication.Stage.ENROLLED
                app.reviewed_by = request.user
                app.notes = "Full 10-step dossier updated & finalized."
                app.save()

                student = Student.objects.filter(first_name=app.first_name, last_name=app.last_name).order_by('-created_at').first()
                if student:
                    student.first_name = first_name
                    student.last_name = last_name
                    student.gender = gender
                    student.date_of_birth = dob
                    student.blood_group = blood_group
                    student.religion = religion
                    student.nationality = nationality
                    student.guardian_name = parent_name
                    student.emergency_contact_name = emergency_contact_name
                    student.emergency_contact_phone = emergency_contact_phone
                    student.residential_address = address
                    if prev_school:
                        student.previous_school_name = prev_school
                    photo_file = request.FILES.get('photo')
                    if photo_file:
                        student.photo = photo_file
                    student.save()
                else:
                    adm_no = f"ADM-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"
                    stu_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
                    student = Student.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        student_id=stu_id,
                        admission_number=adm_no,
                        gender=gender,
                        date_of_birth=dob,
                        blood_group=blood_group,
                        religion=religion,
                        nationality=nationality,
                        guardian_name=parent_name,
                        guardian_relation='Parent',
                        emergency_contact_name=emergency_contact_name,
                        emergency_contact_phone=emergency_contact_phone,
                        residential_address=address,
                        previous_school_name=prev_school,
                        status=Student.Status.ACTIVE,
                        photo=request.FILES.get('photo'),
                        admission_date=timezone.now().date()
                    )
            else:
                app_num = f"ADM-FULL-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:5].upper()}"
                adm_no = f"ADM-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"
                stu_id = f"STU-{uuid.uuid4().hex[:6].upper()}"

                app = AdmissionsApplication.objects.create(
                    application_number=app_num,
                    academic_year=year_obj,
                    applying_for_class=class_obj,
                    first_name=first_name,
                    last_name=last_name,
                    gender=gender,
                    date_of_birth=dob,
                    parent_name=parent_name,
                    parent_phone=parent_phone,
                    parent_email=parent_email,
                    residential_address=address,
                    previous_school=f"{prev_school} ({prev_board}) - Last Grade: {last_grade}, TC: {tc_number}",
                    status=AdmissionsApplication.Stage.ENROLLED,
                    reviewed_by=request.user,
                    notes=f"Full 10-step dossier verified. Enrolled directly."
                )

                photo_file = request.FILES.get('photo')
                student = Student.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    student_id=stu_id,
                    admission_number=adm_no,
                    gender=gender,
                    date_of_birth=dob,
                    blood_group=blood_group,
                    religion=religion,
                    nationality=nationality,
                    guardian_name=parent_name,
                    guardian_relation='Parent',
                    emergency_contact_name=emergency_contact_name,
                    emergency_contact_phone=emergency_contact_phone,
                    residential_address=address,
                    previous_school_name=prev_school,
                    status=Student.Status.ACTIVE,
                    photo=photo_file,
                    admission_date=timezone.now().date()
                )

            # Update / Create StudentEnrollment
            if section_obj and year_obj:
                enrollment, _ = StudentEnrollment.objects.get_or_create(
                    student=student,
                    academic_year=year_obj,
                    defaults={
                        'section': section_obj,
                        'roll_number': str(StudentEnrollment.objects.filter(section=section_obj, academic_year=year_obj).count() + 1)
                    }
                )
                if enrollment.section != section_obj:
                    enrollment.section = section_obj
                    enrollment.save()

            # Process Uploaded Documents
            from documents.models import SchoolDocument, DocumentCategory
            doc_map = [
                ('transfer_certificate', 'Transfer Certificate', 'Transfer Certificates'),
                ('marksheet', 'Previous School Marksheet', 'Transcripts & Marksheets'),
                ('character_certificate', 'Character Certificate', 'Certificates'),
                ('birth_certificate', 'Birth Certificate / National ID', 'Identity Proofs'),
            ]
            for file_key, doc_title, cat_name in doc_map:
                uploaded_file = request.FILES.get(file_key)
                if uploaded_file:
                    cat, _ = DocumentCategory.objects.get_or_create(name=cat_name)
                    SchoolDocument.objects.create(
                        title=f"{student.full_name} - {doc_title}",
                        category=cat,
                        document_file=uploaded_file,
                        student=student,
                        uploaded_by=request.user,
                        access_level=SchoolDocument.AccessLevel.STAFF_ONLY,
                        description=f"Uploaded during Full Admission enrollment for {student.admission_number}."
                    )

            log_audit(
                request,
                action=AuditLog.Action.CREATE if not existing_app_id else AuditLog.Action.UPDATE,
                module='Admissions',
                model_name='Student',
                object_id=str(student.id),
                object_repr=f"Full Admission Enrollment: {student.full_name} ({student.admission_number})"
            )

        messages.success(request, f"Student '{student.full_name}' successfully updated & full admission dossier finalized!")
        return redirect('admissions:admission_success', app_num=app.application_number)


class AdmissionSuccessView(SchoolAdminRequiredMixin, TemplateView):
    """
    Post-Admission Confirmation & Official Enrollment Receipt.
    """
    template_name = 'admissions/admission_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_num = self.kwargs.get('app_num')
        app = AdmissionsApplication.objects.filter(application_number=app_num).first()
        student = None
        if app:
            student = Student.objects.filter(first_name=app.first_name, last_name=app.last_name).order_by('-created_at').first()

        is_quick_mode = app.application_number.startswith('ADM-QUICK') if app else False

        context.update({
            'app_num': app_num,
            'app': app,
            'student': student,
            'is_quick_mode': is_quick_mode,
            'student_name': app.applicant_full_name if app else (student.full_name if student else 'Student'),
            'admission_no': student.admission_number if student else f"ADM-{timezone.now().strftime('%Y')}-0419",
            'roll_no': student.student_id if student else f"STU-{timezone.now().strftime('%Y')}-0419",
            'class_name': app.applying_for_class.name if (app and app.applying_for_class) else 'Grade 9 - Section A',
            'admission_date': student.admission_date if student else timezone.now().date(),
            'fee_amount': Decimal('29500.00'),
        })
        return context



class AdmissionsApplicationCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ANONYMOUS']
    model = AdmissionsApplication
    form_class = AdmissionsApplicationForm
    template_name = 'admissions/application_form.html'
    success_url = reverse_lazy('admissions:pipeline')

    def form_valid(self, form):
        app = form.save(commit=False)
        app.application_number = f"APP-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"
        app.save()
        messages.success(self.request, f"Admissions application {app.application_number} submitted successfully.")
        return redirect('admissions:pipeline')


class AdmissionsApplicationDetailView(SchoolAdminRequiredMixin, DetailView):
    model = AdmissionsApplication
    template_name = 'admissions/application_detail.html'
    context_object_name = 'app'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['review_form'] = AdmissionsReviewForm(instance=self.object)
        suggested_adm = f"ADM-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"
        suggested_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
        context['convert_form'] = AdmissionsConvertStudentForm(initial={
            'admission_number': suggested_adm,
            'student_id': suggested_id,
            'roll_number': 1
        })
        context['sections'] = self.object.applying_for_class.sections.filter(is_deleted=False)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = AdmissionsReviewForm(request.POST, instance=self.object)
        if form.is_valid():
            app = form.save(commit=False)
            app.reviewed_by = request.user
            app.save()
            messages.success(request, f"Application {app.application_number} status updated to {app.get_status_display()}.")
            return redirect('admissions:detail', pk=app.pk)
        return self.get(request, *args, **kwargs)


class AdmissionsConvertStudentView(SchoolAdminRequiredMixin, View):
    """
    Enrolls an approved applicant into the active student directory.
    """
    def post(self, request, pk):
        app = get_object_or_404(AdmissionsApplication, pk=pk, is_deleted=False)
        form = AdmissionsConvertStudentForm(request.POST)
        
        if form.is_valid():
            section = form.cleaned_data['section']
            roll_no = form.cleaned_data['roll_number']
            admission_no = form.cleaned_data['admission_number']
            student_id = form.cleaned_data['student_id']
            
            with transaction.atomic():
                student = Student.objects.create(
                    first_name=app.first_name,
                    last_name=app.last_name,
                    gender=app.gender,
                    date_of_birth=app.date_of_birth,
                    student_id=student_id,
                    admission_number=admission_no,
                    status=Student.Status.ACTIVE,
                    admission_date=timezone.now().date(),
                    residential_address=app.residential_address,
                    emergency_contact_name=app.parent_name,
                    emergency_contact_phone=app.parent_phone,
                    emergency_contact_relation='Parent/Guardian',
                    previous_school_name=app.previous_school
                )
                
                StudentEnrollment.objects.create(
                    student=student,
                    academic_year=app.academic_year,
                    section=section,
                    roll_number=roll_no
                )
                
                app.status = AdmissionsApplication.Stage.ENROLLED
                app.save()
                
                log_audit(
                    request,
                    action=AuditLog.Action.CREATE,
                    module='Admissions',
                    model_name='Student',
                    object_id=str(student.id),
                    object_repr=f"Converted Applicant {app.application_number} to Student {student.full_name} ({student.admission_number})"
                )
                
            messages.success(request, f"Applicant successfully converted to Student: {student.full_name} ({student.admission_number})")
            return redirect('students:student_detail', pk=student.pk)
            
        messages.error(request, "Failed to convert applicant. Please check the entered details.")
        return redirect('admissions:detail', pk=app.pk)


class AdmissionsPrintView(SchoolAdminRequiredMixin, DetailView):
    """
    Renders the official printable admission confirmation dossier for an AdmissionsApplication.
    """
    model = AdmissionsApplication
    template_name = 'admissions/admission_print.html'
    context_object_name = 'app'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or self.object.academic_year or AcademicYear.objects.filter(is_current=True).first()
        student = Student.objects.filter(admission_number=self.object.application_number).first()
        context.update({
            'academic_year': academic_year,
            'student': student,
        })
        return context


class StudentAdmissionPrintView(SchoolAdminRequiredMixin, DetailView):
    """
    Renders the official printable admission confirmation dossier directly from a Central Student Record.
    """
    model = Student
    template_name = 'admissions/admission_print.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        app = AdmissionsApplication.objects.filter(first_name__iexact=self.object.first_name, last_name__iexact=self.object.last_name).first()
        context.update({
            'academic_year': academic_year,
            'app': app,
        })
        return context

