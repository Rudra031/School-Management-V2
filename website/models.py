import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

class WebsiteThemeConfig(BaseModel):
    """
    Global visual styling, colors, typography, layout, and 3D WebGL engine configuration.
    Controlled via the No-Code Visual Studio Customizer.
    """
    class Preset(models.TextChoices):
        ACADEMIC_PRESTIGE = 'ACADEMIC_PRESTIGE', _('Academic Prestige (Dark Slate & Gold)')
        MODERN_BLUE = 'MODERN_BLUE', _('Modern Blue (Navy & Indigo)')
        EMERALD_ACADEMY = 'EMERALD_ACADEMY', _('Emerald Academy (Forest & Sage)')
        MINIMAL_LIGHT = 'MINIMAL_LIGHT', _('Minimal Light (Clean White & Slate)')
        PREMIUM_DARK = 'PREMIUM_DARK', _('Premium Dark (Obsidian & Cyan)')

    class ThreeBackgroundMode(models.TextChoices):
        POLYHEDRA = 'POLYHEDRA', _('Floating Geometric Polyhedra & Nebula')
        PARTICLES = 'PARTICLES', _('Ambient Particle Vortex')
        MINIMAL_GRID = 'MINIMAL_GRID', _('Minimal 3D Horizon Grid')
        STATIC_GRADIENT = 'STATIC_GRADIENT', _('Static Luxury CSS Mesh Gradient (No WebGL)')

    name = models.CharField(max_length=100, default="Active Website Theme")
    is_active = models.BooleanField(default=True)
    preset_name = models.CharField(max_length=50, choices=Preset.choices, default=Preset.ACADEMIC_PRESTIGE)

    # Color Palette
    primary_color = models.CharField(max_length=20, default="#0F172A", help_text="Deep canvas / dominant branding color")
    secondary_color = models.CharField(max_length=20, default="#1E293B", help_text="Card surfaces and secondary panels")
    accent_color = models.CharField(max_length=20, default="#4F46E5", help_text="Action items, buttons, active states")
    tertiary_color = models.CharField(max_length=20, default="#EAB308", help_text="High prestige / honors / gold highlights")
    surface_color = models.CharField(max_length=20, default="#051424", help_text="Background base surface")
    text_color = models.CharField(max_length=20, default="#D4E4FA", help_text="Main heading and body typography color")
    muted_text_color = models.CharField(max_length=20, default="#94A3B8", help_text="Muted captions and labels")

    # Typography Engine
    font_family_heading = models.CharField(max_length=100, default="'Geist', 'Hanken Grotesk', sans-serif")
    font_family_body = models.CharField(max_length=100, default="'Inter', sans-serif")
    font_size_base = models.CharField(max_length=20, default="16px")
    heading_scale = models.FloatField(default=1.25, help_text="Multiplier for headline scales")

    # Spacing & Layout
    container_width = models.CharField(max_length=20, default="1280px")
    section_padding = models.CharField(max_length=20, default="80px")
    card_radius = models.CharField(max_length=20, default="14px")
    button_radius = models.CharField(max_length=20, default="8px")

    # 3D Three.js WebGL Engine Parameters
    three_enabled = models.BooleanField(default=True, help_text="Enable interactive 3D WebGL hero background")
    three_background_mode = models.CharField(max_length=30, choices=ThreeBackgroundMode.choices, default=ThreeBackgroundMode.POLYHEDRA)
    three_particle_count = models.IntegerField(default=450, help_text="Particle count (100 to 1200)")
    three_camera_sensitivity = models.FloatField(default=1.0, help_text="Mouse parallax sensitivity factor")
    enable_reduced_motion_fallback = models.BooleanField(default=True, help_text="Auto fallback on reduced motion / mobile")

    # Custom Code Injections
    custom_css = models.TextField(blank=True, help_text="Custom CSS overrides injected into the public template")
    custom_js = models.TextField(blank=True, help_text="Custom analytics or scripts")

    class Meta:
        verbose_name = _('Website Theme Configuration')
        verbose_name_plural = _('Website Theme Configurations')

    def __str__(self):
        return f"{self.name} ({self.get_preset_name_display()})"

    @classmethod
    def get_active(cls):
        theme = cls.objects.filter(is_active=True).first()
        if not theme:
            theme = cls.objects.create(name="Default Institutional Theme", is_active=True)
        return theme

    def get_css_variables(self):
        """Returns a string of CSS custom properties for dynamic injection."""
        return f"""
        :root {{
          --site-primary: {self.primary_color};
          --site-secondary: {self.secondary_color};
          --site-accent: {self.accent_color};
          --site-gold: {self.tertiary_color};
          --site-surface: {self.surface_color};
          --site-text: {self.text_color};
          --site-text-muted: {self.muted_text_color};
          --site-font-heading: {self.font_family_heading};
          --site-font-body: {self.font_family_body};
          --site-container-max: {self.container_width};
          --site-section-padding: {self.section_padding};
          --site-radius-card: {self.card_radius};
          --site-radius-btn: {self.button_radius};
        }}
        """


class WebsitePage(BaseModel):
    """
    Public website virtual pages (Home, About, Academics, Admissions, Faculty, Campus Life, News, Testimonials, Contact).
    """
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=150)
    nav_label = models.CharField(max_length=80)
    nav_order = models.IntegerField(default=0)
    is_in_nav = models.BooleanField(default=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['nav_order', 'title']
        verbose_name = _('Website Page')
        verbose_name_plural = _('Website Pages')

    def __str__(self):
        return f"{self.title} (/{self.slug}/)"


class WebsiteSection(BaseModel):
    """
    Configurable modular section component on a page.
    """
    class SectionType(models.TextChoices):
        HERO_3D = 'HERO_3D', _('3D Interactive Hero Experience')
        METRICS_BANNER = 'METRICS_BANNER', _('Floating Key Metrics Banner')
        SMART_TICKER = 'SMART_TICKER', _('Smart Live Announcements Ticker')
        ABOUT_STORY = 'ABOUT_STORY', _('About & Institutional Pillars')
        PRINCIPAL_MESSAGE = 'PRINCIPAL_MESSAGE', _('Principal / Leadership Spotlight')
        ACADEMICS_TIERS = 'ACADEMICS_TIERS', _('Academic Programs & Curriculum Matrix')
        ADMISSIONS_ROADMAP = 'ADMISSIONS_ROADMAP', _('6-Stage Interactive Admissions Funnel')
        FACULTY_ROSTER = 'FACULTY_ROSTER', _('Faculty & Academic Chairs Directory')
        CAMPUS_LIFE_GRID = 'CAMPUS_LIFE_GRID', _('Campus Life & World-Class Facilities')
        NEWS_EVENTS_HUB = 'NEWS_EVENTS_HUB', _('Dynamic News & Upcoming Events')
        TESTIMONIALS_CAROUSEL = 'TESTIMONIALS_CAROUSEL', _('Testimonials & Alumni Stories')
        CONTACT_MAP = 'CONTACT_MAP', _('Interactive Campus Map & Inquiry Lead Form')
        CTA_BANNER = 'CTA_BANNER', _('Call-to-Action Enrollment Banner')
        CUSTOM_BLOCK = 'CUSTOM_BLOCK', _('Custom Content Block')

    page = models.ForeignKey(WebsitePage, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=50, choices=SectionType.choices, default=SectionType.HERO_3D)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    content_json = models.JSONField(default=dict, blank=True)
    custom_css = models.TextField(blank=True)

    class Meta:
        ordering = ['page', 'order']
        verbose_name = _('Website Section')
        verbose_name_plural = _('Website Sections')

    def __str__(self):
        return f"[{self.page.slug}] {self.get_section_type_display()} - {self.title}"


class PublicNewsArticle(BaseModel):
    """
    Dynamic news article and announcement system.
    """
    class Category(models.TextChoices):
        ACADEMIC = 'ACADEMIC', _('Academic Excellence')
        ACHIEVEMENT = 'ACHIEVEMENT', _('Institutional Achievements')
        CAMPUS_LIFE = 'CAMPUS_LIFE', _('Campus Life & Culture')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Official Notice & Circular')
        INNOVATION = 'INNOVATION', _('STEM & Innovation')

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.ACADEMIC)
    author_name = models.CharField(max_length=120, default="Apex Communications Bureau")
    excerpt = models.TextField(help_text="Short summary for card previews")
    content = models.TextField()
    featured_image_url = models.CharField(max_length=500, blank=True, help_text="Image URL or media asset path")
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-published_at']
        verbose_name = _('Public News Article')
        verbose_name_plural = _('Public News Articles')

    def __str__(self):
        return f"[{self.category}] {self.title}"


class PublicEvent(BaseModel):
    """
    Dynamic school event, symposium, and calendar scheduling entity.
    """
    class Category(models.TextChoices):
        SYMPOSIUM = 'SYMPOSIUM', _('Science & Academic Symposium')
        ARTS_CULTURE = 'ARTS_CULTURE', _('Arts & Cultural Festival')
        ATHLETICS = 'ATHLETICS', _('Sports & Athletic Championship')
        OPEN_HOUSE = 'OPEN_HOUSE', _('Admissions Open House & Campus Tour')
        EXAMINATION = 'EXAMINATION', _('Examination Schedule & Key Dates')
        COMMENCEMENT = 'COMMENCEMENT', _('Commencement & Graduation')

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.SYMPOSIUM)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=200, default="Grand Academic Auditorium & Virtual Stream")
    description = models.TextField()
    registration_link = models.CharField(max_length=500, blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_datetime']
        verbose_name = _('Public Event')
        verbose_name_plural = _('Public Events')

    def __str__(self):
        return f"{self.title} ({self.start_datetime.strftime('%b %d, %Y')})"


class PublicFacultyProfile(BaseModel):
    """
    Showcase faculty profiles, chairpersons, and research leads.
    """
    class Department(models.TextChoices):
        SCIENCES = 'SCIENCES', _('Natural & Applied Sciences')
        MATHEMATICS = 'MATHEMATICS', _('Pure & Computational Mathematics')
        HUMANITIES = 'HUMANITIES', _('Humanities & Social Sciences')
        LANGUAGES = 'LANGUAGES', _('World Languages & Literature')
        ARTS = 'ARTS', _('Visual & Performing Arts')
        ATHLETICS = 'ATHLETICS', _('Athletics & Physical Education')
        LEADERSHIP = 'LEADERSHIP', _('Academic Leadership & Deans')

    name = models.CharField(max_length=120)
    designation = models.CharField(max_length=150)
    department = models.CharField(max_length=40, choices=Department.choices, default=Department.SCIENCES)
    qualification = models.CharField(max_length=150, help_text="e.g. Ph.D. Harvard University, M.Sc. Oxford")
    experience_years = models.IntegerField(default=12)
    photo_url = models.CharField(max_length=500, blank=True)
    bio = models.TextField()
    email = models.EmailField(blank=True)
    order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('Public Faculty Profile')
        verbose_name_plural = _('Public Faculty Profiles')

    def __str__(self):
        return f"{self.name} - {self.designation}"


class PublicTestimonial(BaseModel):
    """
    Verified reviews and inspiring stories from parents, alumni, and students.
    """
    class RoleType(models.TextChoices):
        PARENT = 'PARENT', _('Parent / Guardian')
        STUDENT = 'STUDENT', _('Current Student')
        ALUMNI = 'ALUMNI', _('Distinguished Alumni')
        EDUCATOR = 'EDUCATOR', _('Guest Academic / Scholar')

    author_name = models.CharField(max_length=120)
    role_type = models.CharField(max_length=30, choices=RoleType.choices, default=RoleType.PARENT)
    sub_title = models.CharField(max_length=150, help_text="e.g. Parent of IBDP Scholar / MIT Class of '28")
    quote = models.TextField()
    rating = models.IntegerField(default=5)
    graduation_year = models.IntegerField(blank=True, null=True)
    avatar_url = models.CharField(max_length=500, blank=True)
    is_featured = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = _('Public Testimonial')
        verbose_name_plural = _('Public Testimonials')

    def __str__(self):
        return f"{self.author_name} ({self.get_role_type_display()})"


class WebsiteMediaAsset(BaseModel):
    """
    Media library manager for photos, logos, prospectus documents, and campus video tours.
    """
    class AssetType(models.TextChoices):
        IMAGE = 'IMAGE', _('Photography / Graphic')
        HERO_BG = 'HERO_BG', _('Hero Background')
        LOGO = 'LOGO', _('School Crest / Emblem')
        DOCUMENT = 'DOCUMENT', _('PDF Prospectus / Syllabus')
        VIDEO = 'VIDEO', _('Campus Video')

    title = models.CharField(max_length=200)
    file_url = models.CharField(max_length=500)
    asset_type = models.CharField(max_length=30, choices=AssetType.choices, default=AssetType.IMAGE)
    file_size_kb = models.IntegerField(default=0)
    dimensions = models.CharField(max_length=50, blank=True, help_text="e.g. 1920x1080")

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Website Media Asset')
        verbose_name_plural = _('Website Media Assets')

    def __str__(self):
        return f"[{self.asset_type}] {self.title}"


class WebsiteDraftVersion(BaseModel):
    """
    Version control snapshot store for no-code customizer drafts and rollbacks.
    """
    version_tag = models.CharField(max_length=40, default="v1.0")
    snapshot_json = models.JSONField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='website_drafts'
    )
    is_live = models.BooleanField(default=False)
    changelog_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Website Draft Version')
        verbose_name_plural = _('Website Draft Versions')

    def __str__(self):
        status = " [LIVE]" if self.is_live else " [DRAFT]"
        return f"{self.version_tag}{status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class PublicContactInquiry(BaseModel):
    """
    Prospective student and parent lead contact submissions.
    """
    class InquiryType(models.TextChoices):
        ADMISSIONS = 'ADMISSIONS', _('Admissions & Enrollment')
        CAMPUS_TOUR = 'CAMPUS_TOUR', _('Schedule a 3D / Campus Tour')
        ACADEMICS = 'ACADEMICS', _('Academic Curriculum & Syllabi')
        GENERAL = 'GENERAL', _('General Institutional Inquiries')
        CAREERS = 'CAREERS', _('Faculty & Research Positions')

    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    inquiry_type = models.CharField(max_length=40, choices=InquiryType.choices, default=InquiryType.ADMISSIONS)
    grade_interested = models.CharField(max_length=80, blank=True)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Public Contact Inquiry')
        verbose_name_plural = _('Public Contact Inquiries')

    def __str__(self):
        return f"{self.full_name} ({self.get_inquiry_type_display()}) - {self.created_at.strftime('%b %d')}"
