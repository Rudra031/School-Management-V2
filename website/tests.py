from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from website.models import (
    WebsiteThemeConfig, WebsitePage, WebsiteSection,
    PublicNewsArticle, PublicEvent, PublicFacultyProfile,
    PublicTestimonial, PublicContactInquiry, WebsiteDraftVersion
)

User = get_user_model()

class WebsiteModelTests(TestCase):
    def setUp(self):
        self.theme = WebsiteThemeConfig.objects.create(
            name="Test Horizon Theme",
            is_active=True,
            primary_color="#0F172A",
            accent_color="#4F46E5"
        )
        self.page = WebsitePage.objects.create(
            slug="home",
            title="Home",
            nav_label="Home",
            nav_order=1,
            is_published=True
        )

    def test_theme_get_active(self):
        active = WebsiteThemeConfig.get_active()
        self.assertEqual(active.primary_color, "#0F172A")
        self.assertIn("--site-primary", active.get_css_variables())

    def test_page_str(self):
        self.assertEqual(str(self.page), "Home (/home/)")


class PublicWebsiteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.theme = WebsiteThemeConfig.objects.create(
            name="Apex Theme",
            is_active=True
        )
        self.article = PublicNewsArticle.objects.create(
            title="Apex Math Olympiad Victory",
            slug="apex-math-olympiad-victory",
            category=PublicNewsArticle.Category.ACHIEVEMENT,
            excerpt="Our scholars secured top honors.",
            content="Full article content detailing the championship.",
            is_published=True
        )
        self.event = PublicEvent.objects.create(
            title="Science Symposium 2026",
            category=PublicEvent.Category.SYMPOSIUM,
            start_datetime=timezone.now() + timezone.timedelta(days=7),
            location="Auditorium",
            description="Flagship symposium",
            is_published=True
        )
        self.faculty = PublicFacultyProfile.objects.create(
            name="Dr. Eleanor Vance",
            designation="Principal",
            department=PublicFacultyProfile.Department.LEADERSHIP,
            qualification="Ph.D. Harvard",
            bio="Academic leader",
            is_published=True
        )

    def test_public_home_view(self):
        response = self.client.get(reverse('website:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Little Minds Bloom with Joy")
        self.assertContains(response, "Playgroup &amp; Nursery")
        self.assertContains(response, "100% Child-Safe Campus")
        self.assertContains(response, "Verify Transfer Certificate")

    def test_public_about_view(self):
        response = self.client.get(reverse('website:about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cultivating Curiosity, Joy &amp; Character Since 1998")

    def test_public_academics_view(self):
        response = self.client.get(reverse('website:academics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Joyful Foundational Learning")

    def test_public_admissions_view(self):
        response = self.client.get(reverse('website:admissions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The 6-Stage Joyful Admissions Journey")

    def test_public_faculty_view(self):
        response = self.client.get(reverse('website:faculty'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr. Eleanor Vance")

    def test_public_campus_life_view(self):
        response = self.client.get(reverse('website:campus_life'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Treehouse Story Library")

    def test_public_news_events_view(self):
        response = self.client.get(reverse('website:news_events'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Math Olympiad Victory")

    def test_public_news_detail_view(self):
        response = self.client.get(reverse('website:news_detail', kwargs={'slug': self.article.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Math Olympiad Victory")

    def test_public_contact_post_inquiry(self):
        post_data = {
            'full_name': 'Claire Sterling',
            'email': 'claire@example.com',
            'phone': '+1 (555) 234-5678',
            'inquiry_type': 'ADMISSIONS',
            'grade_interested': 'Grade 9',
            'message': 'Interested in IGCSE curriculum details.'
        }
        response = self.client.post(reverse('website:contact'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PublicContactInquiry.objects.filter(email='claire@example.com').exists())

    def test_public_apply_get(self):
        response = self.client.get(reverse('website:public_apply'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online Student Admission Application")
        self.assertContains(response, "Step 1: Academic Stream")

    def test_public_apply_post_valid(self):
        from academics.models import AcademicYear, ClassLevel
        from admissions.models import AdmissionsApplication
        year = AcademicYear.objects.create(name="2026-2027", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
        cls = ClassLevel.objects.create(name="Class IX", numeric_level=9)

        post_data = {
            'academic_year': year.id,
            'applying_for_class': cls.id,
            'first_name': 'Rohan',
            'last_name': 'Mukherjee',
            'gender': 'MALE',
            'date_of_birth': '2012-08-15',
            'blood_group': 'O+',
            'caste_category': 'General',
            'parent_name': 'Debashis Mukherjee',
            'parent_phone': '+91 98300 44556',
            'parent_email': 'debashis@example.com',
            'residential_address': 'Flat 4B, South City Residency, Prince Anwar Shah Road',
            'city': 'Kolkata',
            'state': 'West Bengal',
            'pin_code': '700068',
            'previous_school': 'St. Xavier Collegiate School',
            'previous_board': 'CBSE',
            'previous_percentage': '94.50',
            'tc_status': 'WILL_SUBMIT',
            'parent_declaration': True,
        }
        response = self.client.post(reverse('website:public_apply'), data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        app = AdmissionsApplication.objects.filter(first_name='Rohan', last_name='Mukherjee').first()
        self.assertIsNotNone(app)
        self.assertTrue(app.application_number.startswith('HPS-APP-'))
        self.assertEqual(app.status, 'SUBMITTED')
        self.assertContains(response, "Application Registered Successfully")
        self.assertContains(response, app.application_number)

    def test_public_apply_track(self):
        from academics.models import AcademicYear, ClassLevel
        from admissions.models import AdmissionsApplication
        year, _ = AcademicYear.objects.get_or_create(name="2026-2027", defaults={'start_date': "2026-04-01", 'end_date': "2027-03-31", 'is_current': True})
        cls, _ = ClassLevel.objects.get_or_create(name="Class VI", defaults={'numeric_level': 6})
        app = AdmissionsApplication.objects.create(
            application_number="HPS-APP-2026-99881",
            academic_year=year,
            applying_for_class=cls,
            first_name="Ananya",
            last_name="Sen",
            gender="FEMALE",
            date_of_birth="2015-06-20",
            parent_name="Dr. Joydeep Sen",
            parent_phone="+91 98311 22334",
            parent_email="sen@example.com",
            residential_address="Kolkata",
            status=AdmissionsApplication.Stage.SUBMITTED
        )

        response = self.client.get(reverse('website:public_apply_track') + f"?app_num={app.application_number}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ananya Sen")
        self.assertContains(response, "Submitted")


class WebsiteCustomizerAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='admin@school.edu',
            password='Password123!',
            username='webadmin'
        )
        self.theme = WebsiteThemeConfig.objects.create(
            name="Active Theme",
            is_active=True,
            primary_color="#0F172A"
        )

    def test_customizer_studio_requires_auth(self):
        response = self.client.get(reverse('website:customizer_studio'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_customizer_studio_authenticated(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('website:customizer_studio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apex Site Editor")

    def test_customizer_save_draft_api(self):
        self.client.force_login(self.admin_user)
        payload = {
            'version_tag': 'Draft v2.5',
            'primary_color': '#0284c7',
            'accent_color': '#2563eb'
        }
        response = self.client.post(
            reverse('website:api_save_draft'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(WebsiteDraftVersion.objects.filter(version_tag='Draft v2.5').exists())

    def test_customizer_publish_api(self):
        self.client.force_login(self.admin_user)
        payload = {
            'primary_color': '#064e3b',
            'surface_color': '#022c22',
            'accent_color': '#059669',
            'tertiary_color': '#34d399',
            'font_family_heading': "'Geist', sans-serif",
            'font_family_body': "'Inter', sans-serif",
            'container_width': '1440px',
            'section_padding': '90px',
            'card_radius': '16px',
            'button_radius': '10px',
            'three_enabled': True,
            'three_particle_count': 600,
            'three_camera_sensitivity': 1.2,
            'three_background_mode': 'POLYHEDRA',
            'enable_reduced_motion_fallback': True
        }
        response = self.client.post(
            reverse('website:api_publish'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify changes persisted to live model
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.primary_color, '#064e3b')
        self.assertEqual(self.theme.card_radius, '16px')
        self.assertEqual(self.theme.three_particle_count, 600)
