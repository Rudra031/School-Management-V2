from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from website.models import (
    WebsiteThemeConfig, WebsitePage, WebsiteSection,
    PublicNewsArticle, PublicEvent, PublicFacultyProfile,
    PublicTestimonial, WebsiteMediaAsset
)

class Command(BaseCommand):
    help = 'Seeds initial public website pages, sections, theme, and dynamic content'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Modern 3D School Website data...")

        # 1. Theme Configuration
        theme, _ = WebsiteThemeConfig.objects.get_or_create(
            is_active=True,
            defaults={
                'name': 'Apex Horizon Luxury Academic Theme',
                'preset_name': WebsiteThemeConfig.Preset.ACADEMIC_PRESTIGE,
                'primary_color': '#0F172A',
                'secondary_color': '#1E293B',
                'accent_color': '#4F46E5',
                'tertiary_color': '#EAB308',
                'surface_color': '#051424',
                'text_color': '#D4E4FA',
                'muted_text_color': '#94A3B8',
                'font_family_heading': "'Geist', 'Hanken Grotesk', sans-serif",
                'font_family_body': "'Inter', sans-serif",
                'three_enabled': True,
                'three_background_mode': WebsiteThemeConfig.ThreeBackgroundMode.POLYHEDRA,
                'three_particle_count': 500,
                'three_camera_sensitivity': 1.0,
                'enable_reduced_motion_fallback': True,
            }
        )

        # 2. Public Pages
        pages_data = [
            ('home', 'Home', 'Home', 1, True, 'Welcome to Apex Horizon International Academy - A Premier K-12 World School.'),
            ('about', 'About the Academy', 'About', 2, True, 'Discover our heritage, mission, vision, and world-class academic leadership.'),
            ('academics', 'Academic Programs & Curriculum', 'Academics', 3, True, 'Comprehensive primary, middle, high school, and Senior IB/AP pathways.'),
            ('admissions', 'Admissions & Enrollment', 'Admissions', 4, True, 'Transparent 6-stage admissions roadmap, scholarships, and application portal.'),
            ('faculty', 'Faculty & Academic Chairs', 'Faculty', 5, True, 'Meet our distinguished educators, department heads, and research fellows.'),
            ('campus-life', 'Campus Life & World-Class Facilities', 'Campus Life', 6, True, 'Explore our cutting-edge labs, Olympic athletic complex, and student culture.'),
            ('events-news', 'Events & News Hub', 'News & Events', 7, True, 'Stay updated with upcoming symposiums, achievements, and notices.'),
            ('testimonials', 'Testimonials & Alumni Stories', 'Stories', 8, True, 'Inspiring voices from parents, students, and distinguished alumni worldwide.'),
            ('contact', 'Contact & Campus Location', 'Contact', 9, True, 'Connect with admissions counselors, schedule visits, and access campus maps.'),
        ]

        pages_dict = {}
        for slug, title, nav_label, nav_order, in_nav, meta_desc in pages_data:
            page, _ = WebsitePage.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'nav_label': nav_label,
                    'nav_order': nav_order,
                    'is_in_nav': in_nav,
                    'meta_description': meta_desc,
                    'is_published': True
                }
            )
            pages_dict[slug] = page

        # 3. Dynamic News Articles
        news_items = [
            (
                "Apex Horizon Scholars Clinch Gold at International Mathematics Olympiad 2026",
                "apex-scholars-clinch-gold-imo-2026",
                PublicNewsArticle.Category.ACHIEVEMENT,
                "Representing the nation, our Senior Baccalaureate mathematics delegation secured 4 gold and 2 silver medals at the 67th International Olympiad.",
                "Apex Horizon International Academy is proud to announce that our senior student delegation has achieved historic acclaim at the International Mathematics Olympiad (IMO). Competing against 112 international delegations, our scholars demonstrated extraordinary mastery across combinatorial analysis, algebraic geometry, and number theory.",
                True
            ),
            (
                "Inauguration of the Quantum Computing & AI Robotics Innovation Laboratory",
                "quantum-computing-ai-robotics-lab-inauguration",
                PublicNewsArticle.Category.INNOVATION,
                "Equipped with cryogenic quantum simulation arrays and edge-AI compute clusters, the new facility fosters interdisciplinary student research.",
                "In partnership with leading global technology institutes, Apex Horizon has officially opened its state-of-the-art Quantum Computing & AI Robotics Research Wing. Designed for Grade 9 through 12 scholars, the lab bridges theoretical physics with real-world autonomous robotics and machine learning.",
                True
            ),
            (
                "Admissions Open for Academic Session 2026–2027: Early Decision Round",
                "admissions-open-academic-session-2026-2027",
                PublicNewsArticle.Category.ANNOUNCEMENT,
                "Prospective families can now initiate the streamlined 6-stage application process for Kindergarten through Grade 12.",
                "The Admissions Directorate at Apex Horizon International Academy has formally opened application registrations for the 2026–2027 academic session. We welcome diverse, inquisitive minds from around the globe to experience our holistic educational ecosystem.",
                True
            ),
        ]

        for title, slug, cat, excerpt, content, feat in news_items:
            PublicNewsArticle.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'category': cat,
                    'excerpt': excerpt,
                    'content': content,
                    'is_featured': feat,
                    'is_published': True,
                    'views_count': 1420
                }
            )

        # 4. Dynamic Events
        now = timezone.now()
        events_data = [
            (
                "Annual International Science & AI Symposium 2026",
                PublicEvent.Category.SYMPOSIUM,
                now + timedelta(days=14),
                now + timedelta(days=16),
                "Grand Academic Auditorium & Global Metaverse Livestream",
                "A 3-day flagship academic symposium featuring keynote lectures from Nobel Laureates and student research exhibitions.",
                True
            ),
            (
                "Spring Term Admissions Open House & Campus 3D Walkthrough",
                PublicEvent.Category.OPEN_HOUSE,
                now + timedelta(days=7),
                now + timedelta(days=7, hours=4),
                "Admissions Directorate & Campus Center",
                "Meet department deans, tour our research laboratories, and participate in personalized admissions counseling workshops.",
                True
            ),
            (
                "Inter-School Performing Arts Festival & Symphony Showcase",
                PublicEvent.Category.ARTS_CULTURE,
                now + timedelta(days=28),
                now + timedelta(days=29),
                "Black Box Concert Theatre",
                "An evening of classical orchestral performances, contemporary dance, and student theatrical productions.",
                False
            ),
        ]

        for title, cat, start, end, loc, desc, feat in events_data:
            PublicEvent.objects.get_or_create(
                title=title,
                defaults={
                    'category': cat,
                    'start_datetime': start,
                    'end_datetime': end,
                    'location': loc,
                    'description': desc,
                    'is_featured': feat,
                    'is_published': True
                }
            )

        # 5. Public Faculty Profiles
        faculty_data = [
            ("Dr. Arthur Vance", "Chairperson, Theoretical Physics & Quantum Sciences", PublicFacultyProfile.Department.SCIENCES, "Ph.D. Cambridge University, Postdoc MIT", 18, "Leading international researcher in quantum optics and high-energy physics, passionate about mentoring young scholars."),
            ("Prof. Elena Rostova", "Head of Pure & Applied Mathematics", PublicFacultyProfile.Department.MATHEMATICS, "M.Sc. Oxford University, Ph.D. ETH Zürich", 15, "Author of three advanced calculus textbooks, coordinator for global mathematics olympiad coaching."),
            ("Dr. Marcus Sterling", "Dean of Academic Affairs & IB Diploma Coordinator", PublicFacultyProfile.Department.LEADERSHIP, "Ed.D. Harvard Graduate School of Education", 22, "Dedicated to innovative pedagogy, interdisciplinary curriculum design, and university matriculation counseling."),
            ("Sarah Lin, M.F.A.", "Director of Performing Arts & Classical Symphony", PublicFacultyProfile.Department.ARTS, "M.F.A. Juilliard School", 12, "Award-winning composer and orchestral conductor fostering creative confidence in every learner."),
        ]

        for name, desig, dept, qual, exp, bio in faculty_data:
            PublicFacultyProfile.objects.get_or_create(
                name=name,
                defaults={
                    'designation': desig,
                    'department': dept,
                    'qualification': qual,
                    'experience_years': exp,
                    'bio': bio,
                    'is_published': True
                }
            )

        # 6. Public Testimonials
        testimonials_data = [
            ("Jonathan & Claire Sterling", PublicTestimonial.RoleType.PARENT, "Parents of Grade 10 & IBDP Scholars", "Apex Horizon provides an intellectual ecosystem that challenges our children while nurturing their individuality. The balance of academic rigor, character building, and faculty mentorship is simply unmatched.", 5, None),
            ("Sophia Chen", PublicTestimonial.RoleType.ALUMNI, "Class of 2024 • Stanford University Freshman", "The research opportunities and global outlook at Apex Horizon prepared me for the demands of university like nothing else. I discovered my true passion for computational neuroscience right here.", 5, 2024),
            ("David K. Miller", PublicTestimonial.RoleType.PARENT, "Parent of Grade 8 Middle Schooler", "From the transparent admissions process to the daily engagement with teachers, the school feels like a vibrant community dedicated to excellence.", 5, None),
        ]

        for name, role, sub, quote, rating, grad in testimonials_data:
            PublicTestimonial.objects.get_or_create(
                author_name=name,
                defaults={
                    'role_type': role,
                    'sub_title': sub,
                    'quote': quote,
                    'rating': rating,
                    'graduation_year': grad,
                    'is_featured': True
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Modern 3D School Website data!"))
