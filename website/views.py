import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, DetailView, FormView, ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils.decorators import method_decorator

from core.permissions import AdminOrPrincipalRequiredMixin
from website.models import (
    WebsiteThemeConfig, WebsitePage, WebsiteSection,
    PublicNewsArticle, PublicEvent, PublicFacultyProfile,
    PublicTestimonial, WebsiteMediaAsset, WebsiteDraftVersion,
    PublicContactInquiry
)
from academics.models import AcademicYear, ClassLevel
from fees.models import FeeStructure, FeeCategory, FeeConcession

# ==============================================================================
# PUBLIC WEBSITE VIEWS
# ==============================================================================

class PublicWebsiteContextMixin:
    """
    Injects persistent public branding, theme styling, and navigation into all public views.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        theme = WebsiteThemeConfig.get_active()
        context['theme'] = theme
        context['nav_pages'] = WebsitePage.objects.filter(is_published=True, is_in_nav=True).order_by('nav_order')
        context['current_academic_year'] = "Session 2026–2027"
        context['admissions_open'] = True
        context['latest_ticker_news'] = PublicNewsArticle.objects.filter(is_published=True).order_by('-published_at').first()
        context['featured_events'] = PublicEvent.objects.filter(is_published=True, start_datetime__gte=timezone.now()).order_by('start_datetime')[:3]
        return context


@method_decorator(xframe_options_sameorigin, name='dispatch')
class PublicHomeView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Home Page: High-impact Three.js 3D hero WebGL canvas,
    live smart ticker, floating metrics banner, academic tier cards, and testimonials.
    """
    template_name = 'website/public_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'home'
        context['featured_news'] = PublicNewsArticle.objects.filter(is_published=True).order_by('-published_at')[:3]
        context['upcoming_events'] = PublicEvent.objects.filter(is_published=True, start_datetime__gte=timezone.now()).order_by('start_datetime')[:3]
        context['featured_faculty'] = PublicFacultyProfile.objects.filter(is_published=True).order_by('order')[:4]
        context['testimonials'] = PublicTestimonial.objects.filter(is_published=True).order_by('order')[:4]
        return context


class PublicAboutView(PublicWebsiteContextMixin, TemplateView):
    """
    Public About Page: History timeline, mission, vision, core pillars,
    principal's message, and global accreditations.
    """
    template_name = 'website/public_about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'about'
        context['testimonials'] = PublicTestimonial.objects.filter(is_published=True)[:3]
        return context


class PublicAcademicsView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Academics Page: 4-Tier filterable curriculum breakdown
    (Primary, Middle, High, Senior IB/AP) with subject syllabi and pedagogy.
    """
    template_name = 'website/public_academics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'academics'
        return context


class PublicAdmissionsView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Admissions Hub: 6-Stage visual roadmap, real-time dynamic class-wise fee structure,
    interactive installment calculator, scholarships matrix, prospectus download, and counselor consultation.
    """
    template_name = 'website/public_admissions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'admissions'
        
        # Active Academic Session
        active_year = AcademicYear.objects.filter(is_current=True).first() or AcademicYear.objects.first()
        context['active_year'] = active_year
        
        # Class Levels
        classes = list(ClassLevel.objects.filter(is_deleted=False).order_by('numeric_level'))
        categories = list(FeeCategory.objects.all())
        concessions = list(FeeConcession.objects.filter(is_active=True))
        
        # Structures mapped by (class_id)
        class_fee_data = []
        structures = FeeStructure.objects.filter(academic_year=active_year).select_related('class_level', 'fee_category') if active_year else []
        
        struct_by_class = {}
        for s in structures:
            struct_by_class.setdefault(s.class_level_id, []).append(s)
            
        for cl in classes:
            cl_structs = struct_by_class.get(cl.id, [])
            
            # Compute annual, quarterly, and monthly totals
            annual_total = Decimal('0.00')
            monthly_tuition = Decimal('0.00')
            quarterly_total = Decimal('0.00')
            admission_one_time = Decimal('0.00')
            itemized_heads = []
            
            for st in cl_structs:
                amt = st.amount
                freq = st.frequency
                itemized_heads.append({
                    'category_name': st.fee_category.name,
                    'category_type': st.fee_category.category_type,
                    'amount': float(amt),
                    'frequency': st.get_frequency_display(),
                    'frequency_code': freq,
                })
                
                if freq == FeeStructure.Frequency.ONE_TIME:
                    admission_one_time += amt
                elif freq == FeeStructure.Frequency.MONTHLY:
                    monthly_tuition += amt
                    annual_total += amt * 12
                    quarterly_total += amt * 3
                elif freq == FeeStructure.Frequency.QUARTERLY:
                    quarterly_total += amt
                    annual_total += amt * 4
                elif freq == FeeStructure.Frequency.ANNUAL:
                    annual_total += amt
                    quarterly_total += amt / 4
            
            if monthly_tuition == Decimal('0.00') and annual_total > 0:
                monthly_tuition = round(annual_total / 12, 2)
                
            class_fee_data.append({
                'class_id': str(cl.id),
                'name': cl.name,
                'numeric_level': cl.numeric_level,
                'department_name': cl.department.name if cl.department else 'General Academics',
                'annual_total': float(annual_total),
                'quarterly_total': float(quarterly_total),
                'monthly_tuition': float(monthly_tuition),
                'admission_one_time': float(admission_one_time),
                'itemized_heads': itemized_heads,
            })
            
        context['class_fee_data'] = class_fee_data
        context['class_fee_json'] = json.dumps(class_fee_data)
        context['concessions'] = concessions
        context['fee_categories'] = categories
        return context


class PublicAdmissionApplyView(PublicWebsiteContextMixin, FormView):
    """
    Public Online Student Admission Application Portal.
    Allows prospective parents to apply online directly without administrative login.
    """
    template_name = 'website/public_apply.html'
    from admissions.forms import PublicAdmissionApplicationForm
    form_class = PublicAdmissionApplicationForm

    def get_initial(self):
        initial = super().get_initial()
        from academics.models import AcademicYear, ClassLevel
        current_year = AcademicYear.objects.filter(is_current=True).first() or AcademicYear.objects.first()
        if current_year:
            initial['academic_year'] = current_year
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'admissions'
        from academics.models import ClassLevel
        context['class_levels'] = ClassLevel.objects.filter(is_deleted=False).order_by('numeric_level')
        return context

    def form_valid(self, form):
        import uuid
        app = form.save(commit=False)
        current_year = form.cleaned_data.get('academic_year')
        year_str = timezone.now().strftime('%Y')
        app.application_number = f"HPS-APP-{year_str}-{uuid.uuid4().hex[:5].upper()}"
        app.status = 'SUBMITTED'
        app.notes = "Submitted online via Public School Admission Portal."
        app.save()

        messages.success(
            self.request,
            f"Admission Application {app.application_number} submitted successfully! Please save your reference number."
        )
        return redirect('website:public_apply_success', app_num=app.application_number)


class PublicAdmissionSuccessView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Application Submission Confirmation & Printable Acknowledgment Receipt.
    """
    template_name = 'website/public_apply_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'admissions'
        app_num = self.kwargs.get('app_num')
        from admissions.models import AdmissionsApplication
        from core.models import SchoolSetting
        context['app'] = AdmissionsApplication.objects.filter(application_number=app_num).first()
        context['app_num'] = app_num
        context['school_settings'] = SchoolSetting.get_settings()
        context['submission_time'] = timezone.now()
        return context


class PublicAdmissionTrackView(PublicWebsiteContextMixin, View):
    """
    Public Application Status Tracker API & View.
    """
    template_name = 'website/public_apply_track.html'

    def get(self, request, *args, **kwargs):
        from admissions.models import AdmissionsApplication
        app_num = request.GET.get('app_num', '').strip().upper()
        dob = request.GET.get('dob', '').strip()
        app = None
        error_msg = None

        if app_num:
            qs = AdmissionsApplication.objects.filter(application_number=app_num)
            if dob:
                qs = qs.filter(date_of_birth=dob)
            app = qs.first()
            if not app:
                error_msg = f"No application record found matching Reference '{app_num}'."

        context = {
            'active_page': 'admissions',
            'app_num': app_num,
            'dob': dob,
            'app': app,
            'error_msg': error_msg,
        }
        return render(request, self.template_name, context)


class PublicFacultyView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Faculty Directory: Department filters, biographies, qualifications,
    and research chairs.
    """
    template_name = 'website/public_faculty.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'faculty'
        department = self.request.GET.get('dept')
        qs = PublicFacultyProfile.objects.filter(is_published=True)
        if department:
            qs = qs.filter(department=department)
        context['faculty_list'] = qs.order_by('order', 'name')
        context['departments'] = PublicFacultyProfile.Department.choices
        context['selected_dept'] = department or 'ALL'
        return context


class PublicCampusLifeView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Campus Life & Facilities: Labs, libraries, athletic complex,
    creative arts, student clubs, and housing.
    """
    template_name = 'website/public_campus.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'campus-life'
        return context


class PublicNewsEventsView(PublicWebsiteContextMixin, TemplateView):
    """
    Public News & Events Hub: Filterable articles, academic circulars,
    and symposium calendar.
    """
    template_name = 'website/public_news_events.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'events-news'
        category = self.request.GET.get('category')
        news_qs = PublicNewsArticle.objects.filter(is_published=True)
        if category:
            news_qs = news_qs.filter(category=category)
        context['news_articles'] = news_qs.order_by('-published_at')
        context['upcoming_events'] = PublicEvent.objects.filter(is_published=True).order_by('start_datetime')
        context['categories'] = PublicNewsArticle.Category.choices
        context['selected_category'] = category or 'ALL'
        return context


class PublicNewsDetailView(PublicWebsiteContextMixin, DetailView):
    """
    Public News Article Detail View.
    """
    model = PublicNewsArticle
    template_name = 'website/public_news_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'

    def get_object(self):
        obj = super().get_object()
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_news'] = PublicNewsArticle.objects.filter(is_published=True).exclude(pk=self.object.pk)[:3]
        return context


class PublicTestimonialsView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Testimonials & Alumni Stories: Segmented reviews from parents, students, alumni.
    """
    template_name = 'website/public_testimonials.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'testimonials'
        context['testimonials'] = PublicTestimonial.objects.filter(is_published=True).order_by('order')
        return context


class PublicContactView(PublicWebsiteContextMixin, TemplateView):
    """
    Public Contact Page: Campus map, office hours, and inquiry lead form.
    """
    template_name = 'website/public_contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'contact'
        return context

    def post(self, request, *args, **kwargs):
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        inquiry_type = request.POST.get('inquiry_type', 'GENERAL')
        grade = request.POST.get('grade_interested', '').strip()
        message = request.POST.get('message', '').strip()

        if full_name and email and message:
            PublicContactInquiry.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                inquiry_type=inquiry_type,
                grade_interested=grade,
                message=message
            )
            messages.success(request, f"Thank you, {full_name}! Your inquiry has been routed to our Admissions Directorate. We will contact you within 24 hours.")
            return redirect('website:contact')
        else:
            messages.error(request, "Please fill in all required fields.")
            return self.get(request, *args, **kwargs)


# ==============================================================================
# ADMINISTRATOR NO-CODE VISUAL CUSTOMIZER STUDIO VIEWS
# ==============================================================================

class WebsiteCustomizerStudioView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    Administrator No-Code Visual Studio Customizer.
    3-Panel Visual Workspace: Navigator (Left), Live Canvas (Center), Property Inspector (Right).
    """
    template_name = 'website/customizer_studio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        theme = WebsiteThemeConfig.get_active()
        context['theme'] = theme
        context['pages'] = WebsitePage.objects.all().order_by('nav_order')
        context['presets'] = WebsiteThemeConfig.Preset.choices
        context['three_modes'] = WebsiteThemeConfig.ThreeBackgroundMode.choices
        context['latest_draft'] = WebsiteDraftVersion.objects.first()
        context['media_assets'] = WebsiteMediaAsset.objects.all()[:12]
        return context


class WebsiteCustomizerSaveDraftAPI(AdminOrPrincipalRequiredMixin, View):
    """
    AJAX endpoint to save a draft revision of the website theme and section settings.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            theme = WebsiteThemeConfig.get_active()
            
            # Update theme in memory or draft
            draft = WebsiteDraftVersion.objects.create(
                version_tag=data.get('version_tag', f"Draft v{timezone.now().strftime('%H.%M')}"),
                snapshot_json=data,
                created_by=request.user,
                is_live=False,
                changelog_note=data.get('note', 'Visual Studio draft save')
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Draft saved successfully!',
                'draft_id': str(draft.id),
                'version_tag': draft.version_tag,
                'updated_at': timezone.now().strftime('%b %d, %H:%M')
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class WebsiteCustomizerPublishAPI(AdminOrPrincipalRequiredMixin, View):
    """
    AJAX endpoint to publish draft settings to live WebsiteThemeConfig.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            theme = WebsiteThemeConfig.get_active()

            # Apply colors
            theme.primary_color = data.get('primary_color', theme.primary_color)
            theme.secondary_color = data.get('secondary_color', theme.secondary_color)
            theme.accent_color = data.get('accent_color', theme.accent_color)
            theme.tertiary_color = data.get('tertiary_color', theme.tertiary_color)
            theme.surface_color = data.get('surface_color', theme.surface_color)
            theme.text_color = data.get('text_color', theme.text_color)
            
            # Apply typography
            theme.font_family_heading = data.get('font_family_heading', theme.font_family_heading)
            theme.font_family_body = data.get('font_family_body', theme.font_family_body)
            
            # Apply spacing & radius
            theme.container_width = data.get('container_width', theme.container_width)
            theme.section_padding = data.get('section_padding', theme.section_padding)
            theme.card_radius = data.get('card_radius', theme.card_radius)
            theme.button_radius = data.get('button_radius', theme.button_radius)
            
            # Apply 3D params
            theme.three_enabled = data.get('three_enabled', theme.three_enabled)
            theme.three_particle_count = int(data.get('three_particle_count', theme.three_particle_count))
            theme.three_camera_sensitivity = float(data.get('three_camera_sensitivity', theme.three_camera_sensitivity))
            theme.three_background_mode = data.get('three_background_mode', theme.three_background_mode)
            theme.enable_reduced_motion_fallback = data.get('enable_reduced_motion_fallback', theme.enable_reduced_motion_fallback)
            
            theme.save()

            # Create Live Version snapshot
            WebsiteDraftVersion.objects.create(
                version_tag=f"Live v{timezone.now().strftime('%Y%m%d.%H%M')}",
                snapshot_json=data,
                created_by=request.user,
                is_live=True,
                changelog_note="Published to Public Portal"
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Changes published to the public school website successfully!'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class WebsiteCMSDashboardView(AdminOrPrincipalRequiredMixin, TemplateView):
    """
    CMS Management Hub: News articles, events, faculty directory, and contact inquiries.
    """
    template_name = 'website/cms_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = PublicNewsArticle.objects.all().order_by('-published_at')
        context['events'] = PublicEvent.objects.all().order_by('start_datetime')
        context['faculty_members'] = PublicFacultyProfile.objects.all().order_by('order', 'name')
        context['testimonials'] = PublicTestimonial.objects.all().order_by('order')
        context['inquiries'] = PublicContactInquiry.objects.filter(is_resolved=False).order_by('-created_at')
        context['total_inquiries_count'] = PublicContactInquiry.objects.count()
        return context
