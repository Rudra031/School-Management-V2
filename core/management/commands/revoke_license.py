from django.core.management.base import BaseCommand
from core import licensing

class Command(BaseCommand):
    help = 'Deactivate or revoke software license from developer side.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reason',
            type=str,
            default='Terminated by Developer / Subscription Ended',
            help='Reason for revoking software license'
        )
        parser.add_argument(
            '--reset-trial',
            action='store_true',
            help='Reset system back to a fresh 7-day trial mode instead of permanent lockout'
        )

    def handle(self, *args, **options):
        reason = options['reason']
        reset_trial = options['reset_trial']

        msg = licensing.revoke_system_license(reason=reason, reset_trial=reset_trial)

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("  HORIZON SOFTWARE MANAGEMENT — LICENSE DEACTIVATOR"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        if reset_trial:
            self.stdout.write(self.style.WARNING(f"  Status : {msg}"))
        else:
            self.stdout.write(self.style.ERROR(f"  Status : {msg}"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
