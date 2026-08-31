from django.core.management.base import BaseCommand
from accounts.models import User, UserRole
from core.models import SchoolSetting

class Command(BaseCommand):
    help = 'Creates default school settings and 9 demo persona user accounts for testing and evaluation.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Initializing default school settings..."))
        school = SchoolSetting.get_settings()
        school.name = "Apex International Academy"
        school.code = "APEX-2026"
        school.email = "admin@apexacademy.edu"
        school.phone = "+1 (555) 019-2834"
        school.currency_symbol = "$"
        school.currency_code = "USD"
        school.attendance_threshold_percentage = 75.00
        school.save()
        self.stdout.write(self.style.SUCCESS(f"[OK] Configured School Setting: {school.name}"))

        demo_users = [
            {
                'email': 'admin@school.edu',
                'first_name': 'Alexander',
                'last_name': 'Pierce',
                'user_type': UserRole.SUPERADMIN,
                'is_staff': True,
                'is_superuser': True,
                'phone_number': '+1 (555) 100-0001',
            },
            {
                'email': 'principal@school.edu',
                'first_name': 'Eleanor',
                'last_name': 'Vance',
                'user_type': UserRole.PRINCIPAL,
                'is_staff': True,
                'phone_number': '+1 (555) 100-0002',
            },
            {
                'email': 'schooladmin@school.edu',
                'first_name': 'Marcus',
                'last_name': 'Brody',
                'user_type': UserRole.ADMIN,
                'is_staff': True,
                'phone_number': '+1 (555) 100-0003',
            },
            {
                'email': 'teacher@school.edu',
                'first_name': 'Robert',
                'last_name': 'Taylor',
                'user_type': UserRole.TEACHER,
                'phone_number': '+1 (555) 100-0004',
            },
            {
                'email': 'accountant@school.edu',
                'first_name': 'Mary',
                'last_name': 'Major',
                'user_type': UserRole.ACCOUNTANT,
                'phone_number': '+1 (555) 100-0005',
            },
            {
                'email': 'librarian@school.edu',
                'first_name': 'Arthur',
                'last_name': 'Pendelton',
                'user_type': UserRole.LIBRARIAN,
                'phone_number': '+1 (555) 100-0006',
            },
            {
                'email': 'student@school.edu',
                'first_name': 'Lucas',
                'last_name': 'Vance',
                'user_type': UserRole.STUDENT,
                'phone_number': '+1 (555) 100-0007',
            },
            {
                'email': 'parent@school.edu',
                'first_name': 'David',
                'last_name': 'Vance',
                'user_type': UserRole.PARENT,
                'phone_number': '+1 (555) 100-0008',
            },
            {
                'email': 'staff@school.edu',
                'first_name': 'James',
                'last_name': 'Wilson',
                'user_type': UserRole.STAFF,
                'phone_number': '+1 (555) 100-0009',
            },
        ]

        default_password = "Admin@12345"

        self.stdout.write(self.style.NOTICE("Creating 9 Persona Demo Accounts..."))
        for user_data in demo_users:
            email = user_data['email']
            user, created = User.objects.get_or_create(
                email=email,
                defaults=user_data
            )
            user.set_password(default_password)
            user.save()
            status = "Created" if created else "Updated password for"
            self.stdout.write(self.style.SUCCESS(f"[OK] {status} [{user.get_user_type_display()}]: {email}"))

        self.stdout.write(self.style.SUCCESS("\n========================================================"))
        self.stdout.write(self.style.SUCCESS("All 9 Demo Persona Accounts are Ready!"))
        self.stdout.write(self.style.SUCCESS(f"Default Password for all accounts: {default_password}"))
        self.stdout.write(self.style.SUCCESS("========================================================\n"))
