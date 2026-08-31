from django.core.management.base import BaseCommand
from core import licensing

class Command(BaseCommand):
    help = 'Generate a cryptographically signed license key for Horizon School Management System.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-code',
            type=str,
            required=True,
            help='Unique registration code of the school (e.g. HPS-DELHI or * for wildcard)'
        )
        parser.add_argument(
            '--school-name',
            type=str,
            default='',
            help='Official name of the school / institution'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days the license is valid for (default: 365 days)'
        )
        parser.add_argument(
            '--lifetime',
            action='store_true',
            help='Generate a permanent lifetime license (overrides --days)'
        )
        parser.add_argument(
            '--plan',
            type=str,
            default='STANDARD',
            choices=['STANDARD', 'PRO', 'ENTERPRISE', 'EXTENDED_TRIAL', 'REVOKED'],
            help='Plan tier / license category (default: STANDARD)'
        )
        parser.add_argument(
            '--revoke',
            action='store_true',
            help='Generate a cryptographic revocation key (locks software)'
        )
        parser.add_argument(
            '--install-id',
            type=str,
            default='*',
            help='Lock license to a specific server Installation ID (default: * for any machine)'
        )
        parser.add_argument(
            '--max-students',
            type=int,
            default=0,
            help='Student cap (0 for unlimited)'
        )

    def handle(self, *args, **options):
        school_code = options['school_code'].strip().upper()
        school_name = options['school_name'].strip()
        days = options['days']
        is_lifetime = options['lifetime']
        is_revoke = options['revoke']
        plan = 'REVOKED' if is_revoke else options['plan'].strip().upper()
        install_id = options['install_id'].strip().upper()
        max_students = options['max_students']

        payload = licensing.create_license_payload(
            school_code=school_code,
            school_name=school_name,
            plan_type=plan,
            days=days,
            is_lifetime=is_lifetime,
            install_id=install_id,
            max_students=max_students
        )


        signed_key = licensing.sign_license_payload(payload)

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("  HORIZON SOFTWARE MANAGEMENT — LICENSE GENERATOR (OFFICIAL)"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"  • School Code     : {payload['sub']}")
        self.stdout.write(f"  • School Name     : {payload['name']}")
        self.stdout.write(f"  • License Plan    : {payload['plan']}")
        self.stdout.write(f"  • Issued Date     : {payload['issued']}")
        self.stdout.write(f"  • Expiration      : {payload['expires']}")
        self.stdout.write(f"  • Installation ID : {payload['install_id']}")
        self.stdout.write(f"  • Crypto Nonce    : {payload['nonce']} (1-Time Anti-Replay Guard)")
        self.stdout.write(f"  • Student Limit   : {'Unlimited' if max_students == 0 else max_students}")
        self.stdout.write(self.style.SUCCESS("-" * 70))
        self.stdout.write(self.style.WARNING("  GENERATED LICENSE KEY (Provide this exact key to client):"))
        self.stdout.write(self.style.HTTP_INFO(f"\n{signed_key}\n"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("  Instructions for Developer:")
        self.stdout.write("  1. Copy the key above and deliver to the client school.")
        self.stdout.write("  2. Client enters this key into Settings (Tab 11) or Lockout Screen.")
        self.stdout.write("  3. Key is activated once. When expired, client cannot re-use it.")
        self.stdout.write(self.style.SUCCESS("=" * 70))

