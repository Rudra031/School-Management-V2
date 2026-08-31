import base64
import hashlib
import hmac
import json
import uuid
import datetime
from django.conf import settings
from django.utils import timezone

# Default master signing secret (Can be overridden in settings or .env)
DEFAULT_SIGNING_SECRET = getattr(settings, 'LICENSE_SIGNING_SECRET', 'HORIZON_SMS_MASTER_SECURITY_KEY_2026_DEV_SECRET')

# License Plan Types
PLAN_TRIAL = 'TRIAL'
PLAN_STANDARD = 'STANDARD'
PLAN_PRO = 'PRO'
PLAN_ENTERPRISE = 'ENTERPRISE'
PLAN_EXTENDED_TRIAL = 'EXTENDED_TRIAL'

# License Status Types
STATUS_TRIAL_ACTIVE = 'TRIAL_ACTIVE'
STATUS_ACTIVE = 'ACTIVE'
STATUS_TRIAL_EXPIRED = 'TRIAL_EXPIRED'
STATUS_EXPIRED = 'EXPIRED'
STATUS_INVALID = 'INVALID'
STATUS_REVOKED = 'REVOKED'

TRIAL_DAYS = 7


def get_signing_secret():
    """Retrieve secret key used for signing and verifying license keys."""
    return getattr(settings, 'LICENSE_SIGNING_SECRET', DEFAULT_SIGNING_SECRET).encode('utf-8')


def generate_installation_id(school_code=None):
    """
    Generate a stable, unique 16-character Installation ID.
    Format: INST-XXXX-XXXX-XXXX
    """
    salt = school_code or "HORIZON-SMS-DEFAULT-NODE"
    raw = f"{salt}-{uuid.uuid4()}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()
    return f"INST-{digest[0:4]}-{digest[4:8]}-{digest[8:12]}"


def create_license_payload(school_code, school_name="", plan_type=PLAN_STANDARD, days=365, is_lifetime=False, install_id="*", max_students=0):
    """
    Creates a standardized dictionary payload representing the license agreement.
    Includes a unique cryptographic nonce ensuring 1-time anti-replay security.
    """
    now = timezone.now()
    issued_str = now.strftime('%Y-%m-%d')
    
    if is_lifetime:
        expires_str = "LIFETIME"
    else:
        exp_date = now + datetime.timedelta(days=int(days))
        expires_str = exp_date.strftime('%Y-%m-%d')

    payload = {
        "v": 1,
        "sub": str(school_code).strip().upper(),
        "name": str(school_name).strip() if school_name else str(school_code).strip(),
        "plan": str(plan_type).strip().upper(),
        "issued": issued_str,
        "expires": expires_str,
        "install_id": str(install_id).strip().upper() if install_id else "*",
        "max_students": int(max_students),
        "nonce": uuid.uuid4().hex[:12].upper()
    }
    return payload


def sign_license_payload(payload):
    """
    Serializes a license payload to JSON, computes HMAC-SHA256 signature,
    and returns a formatted base64 URL-safe license key token.
    """
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    sig = hmac.new(get_signing_secret(), serialized, hashlib.sha256).digest()
    
    payload_b64 = base64.urlsafe_b64encode(serialized).decode('ascii').rstrip('=')
    sig_b64 = base64.urlsafe_b64encode(sig).decode('ascii').rstrip('=')
    
    return f"HRZN.{payload_b64}.{sig_b64}"


def format_serial_key(raw_token):
    """Converts a raw token to a formatted license key."""
    return raw_token.strip()


def verify_license_key(key_string, current_school_code=None, current_install_id=None, check_consumed=False):
    """
    Validates a license key string.
    Returns: (is_valid: bool, status: str, message: str, payload: dict)
    """
    if not key_string or not isinstance(key_string, str):
        return False, STATUS_INVALID, "No license key provided.", {}

    parts = key_string.strip().split('.')
    if len(parts) != 3 or parts[0] != "HRZN":
        return False, STATUS_INVALID, "Invalid license key format.", {}

    payload_b64 = parts[1]
    provided_sig_b64 = parts[2]

    # Re-pad base64
    def pad_b64(s):
        return s + '=' * ((4 - len(s) % 4) % 4)

    try:
        serialized = base64.urlsafe_b64decode(pad_b64(payload_b64))
        provided_sig = base64.urlsafe_b64decode(pad_b64(provided_sig_b64))
    except Exception:
        return False, STATUS_INVALID, "Corrupted license key encoding.", {}

    # Verify HMAC signature
    expected_sig = hmac.new(get_signing_secret(), serialized, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False, STATUS_INVALID, "License cryptographic signature verification failed.", {}

    # Parse JSON payload
    try:
        payload = json.loads(serialized.decode('utf-8'))
    except Exception:
        return False, STATUS_INVALID, "Invalid payload contents.", {}

    nonce = payload.get("nonce", "")

    # Anti-Replay: Check if nonce was previously consumed and expired
    if check_consumed and nonce:
        from core.models import ConsumedLicenseHistory
        if ConsumedLicenseHistory.objects.filter(nonce=nonce, is_active=False).exists():
            return False, STATUS_EXPIRED, f"This license key (Nonce: {nonce}) has already been consumed and expired. Please obtain a fresh renewal code from the developer.", payload

    # Verify School Code Match (if specified and not wildcard)
    key_school_code = payload.get("sub", "")
    if current_school_code and key_school_code != "*" and key_school_code.upper() != str(current_school_code).strip().upper():
        return False, STATUS_INVALID, f"License was issued for '{key_school_code}', not this school ('{current_school_code}').", payload

    # Verify Installation ID match (if locked to specific machine)
    key_install_id = payload.get("install_id", "*")
    if current_install_id and key_install_id != "*" and key_install_id.upper() != str(current_install_id).strip().upper():
        return False, STATUS_INVALID, "License is locked to a different server installation ID.", payload

    # Verify Expiration
    expires_str = payload.get("expires", "")
    if expires_str != "LIFETIME":
        try:
            exp_date = datetime.datetime.strptime(expires_str, '%Y-%m-%d').date()
            today = timezone.now().date()
            if today > exp_date:
                return False, STATUS_EXPIRED, f"Commercial license expired on {expires_str}.", payload
        except Exception:
            return False, STATUS_INVALID, "Invalid license expiration date format.", payload

    return True, STATUS_ACTIVE, "License verified successfully.", payload


def activate_license_key(key_string, school, user=None):
    """
    One-time activation function:
    1. Cryptographically verifies the license key.
    2. Validates against anti-replay consumed nonce ledger.
    3. Records key in ConsumedLicenseHistory and SoftwareLicense.
    4. Sets status to ACTIVE and updates expiry.
    Returns: (success: bool, message: str, payload: dict)
    """
    from core.models import SoftwareLicense, ConsumedLicenseHistory, AuditLog
    from core.utils import log_audit

    license_obj = SoftwareLicense.get_license()
    
    is_valid, status, msg, payload = verify_license_key(
        key_string,
        current_school_code=school.code,
        current_install_id=license_obj.installation_id,
        check_consumed=True
    )

    if not is_valid:
        return False, msg, payload

    nonce = payload.get("nonce", uuid.uuid4().hex[:12].upper())
    expires_str = payload.get("expires", "LIFETIME")
    plan = payload.get("plan", PLAN_STANDARD)

    # Parse expiration date
    exp_date = None
    if expires_str != "LIFETIME":
        try:
            exp_date = datetime.datetime.strptime(expires_str, '%Y-%m-%d').date()
        except Exception:
            pass

    # If this is a Revocation token issued by developer
    if plan in ('REVOKED', 'REVOKE'):
        license_obj.status = STATUS_REVOKED
        license_obj.license_key = ''
        license_obj.trial_consumed = True
        license_obj.save()
        return True, "🚫 Software license has been officially REVOKED by the developer. System is now locked.", payload

    # Record in ConsumedLicenseHistory ledger
    ConsumedLicenseHistory.objects.update_or_create(
        nonce=nonce,
        defaults={
            'plan_type': plan,
            'licensed_to_code': payload.get('sub', school.code),
            'licensed_to_name': payload.get('name', school.name),
            'issued_date': payload.get('issued', ''),
            'expires_str': expires_str,
            'is_active': True,
            'meta_payload': payload
        }
    )

    # Update SoftwareLicense model
    consumed_list = list(license_obj.consumed_nonces or [])
    if nonce not in consumed_list:
        consumed_list.append(nonce)

    now = timezone.now()
    license_obj.license_key = key_string.strip()
    license_obj.license_type = plan
    license_obj.status = STATUS_ACTIVE
    license_obj.valid_until = exp_date
    license_obj.licensed_to_name = payload.get('name', school.name)
    license_obj.licensed_to_code = payload.get('sub', school.code)
    license_obj.activated_at = now
    license_obj.last_system_time = now
    license_obj.trial_consumed = True
    license_obj.consumed_nonces = consumed_list
    license_obj.meta_payload = payload
    license_obj.save()

    return True, f"🎉 Successfully activated {plan} License! Valid until: {expires_str}.", payload


def revoke_system_license(reason="Revoked by Developer", reset_trial=False):
    """
    Direct developer method to deactivate/revoke software license on server.
    """
    from core.models import SoftwareLicense, ConsumedLicenseHistory
    license_obj = SoftwareLicense.get_license()
    license_obj.license_key = ''
    now = timezone.now()
    
    if reset_trial:
        license_obj.status = STATUS_TRIAL_ACTIVE
        license_obj.license_type = PLAN_TRIAL
        license_obj.trial_start_date = now
        license_obj.trial_end_date = now + datetime.timedelta(days=TRIAL_DAYS)
        license_obj.trial_consumed = False
        license_obj.valid_until = None
        license_obj.save()
        return "License deactivated and system reset to a fresh 7-day trial."
    else:
        license_obj.status = STATUS_REVOKED
        license_obj.valid_until = None
        license_obj.trial_consumed = True
        license_obj.save()
        return f"License revoked and software locked. Reason: {reason}"



def evaluate_system_license():
    """
    Evaluates the complete license health of the system:
    1. Checks for anti-tamper clock rollbacks.
    2. Checks if a valid commercial/extended license is active.
    3. If not, evaluates the 7-day trial period from the initial install date.
    4. Returns a consolidated summary dictionary for middleware and context processors.
    """
    from core.models import SchoolSetting, SoftwareLicense, ConsumedLicenseHistory

    school = SchoolSetting.get_settings()
    school_code = school.code if school else "HPS-DELHI"
    school_name = school.name if school else "Horizon Public School"

    # Get or create software license record
    license_obj = SoftwareLicense.objects.first()
    now = timezone.now()

    if not license_obj:
        # First initialization: Start 7-day trial
        install_id = generate_installation_id(school_code)
        license_obj = SoftwareLicense.objects.create(
            status=STATUS_TRIAL_ACTIVE,
            license_type=PLAN_TRIAL,
            trial_start_date=now,
            trial_end_date=now + datetime.timedelta(days=TRIAL_DAYS),
            trial_consumed=False,
            last_system_time=now,
            installation_id=install_id,
            licensed_to_name=school_name,
            licensed_to_code=school_code
        )

    # Clock Tamper Check (allowing 10 mins grace for NTP clock sync)
    if license_obj.last_system_time and (now < license_obj.last_system_time - datetime.timedelta(minutes=10)):
        return {
            "is_valid": False,
            "is_active": False,
            "is_trial": False,
            "is_expired": True,
            "is_lifetime": False,
            "status": STATUS_INVALID,
            "status_label": "System Clock Tampered",
            "plan_type": license_obj.license_type,
            "school_name": school_name,
            "school_code": school_code,
            "installation_id": license_obj.installation_id,
            "valid_until": None,
            "expires_str": "CLOCK_TAMPER_DETECTED",
            "days_remaining": 0,
            "hours_remaining": 0,
            "message": "System clock manipulation detected. Please correct system time.",
            "license_obj": license_obj
        }

    # Update system time tracker
    if not license_obj.last_system_time or now > license_obj.last_system_time:
        SoftwareLicense.objects.filter(pk=license_obj.pk).update(last_system_time=now)

    # 1. Check if a commercial license key is installed
    if license_obj.license_key:
        is_valid, status, msg, payload = verify_license_key(
            license_obj.license_key,
            current_school_code=school_code,
            current_install_id=license_obj.installation_id
        )
        if is_valid:
            # Valid Commercial / Extended License
            expires_str = payload.get("expires", "LIFETIME")
            valid_until = None
            days_left = 9999
            if expires_str != "LIFETIME":
                try:
                    exp_date = datetime.datetime.strptime(expires_str, '%Y-%m-%d').date()
                    valid_until = exp_date
                    days_left = max(0, (exp_date - now.date()).days)
                except Exception:
                    pass

            return {
                "is_valid": True,
                "is_active": True,
                "is_trial": payload.get("plan") in (PLAN_TRIAL, PLAN_EXTENDED_TRIAL),
                "is_expired": False,
                "is_lifetime": expires_str == "LIFETIME",
                "status": STATUS_ACTIVE,
                "status_label": f"Commercial ({payload.get('plan', 'ACTIVE')})",
                "plan_type": payload.get("plan", PLAN_STANDARD),
                "school_name": payload.get("name", school_name),
                "school_code": payload.get("sub", school_code),
                "installation_id": license_obj.installation_id,
                "valid_until": valid_until,
                "expires_str": expires_str,
                "days_remaining": days_left,
                "hours_remaining": days_left * 24,
                "message": "Commercial license active.",
                "license_obj": license_obj
            }
        else:
            # Installed key has expired -> Mark nonce as consumed/inactive in ledger
            nonce = payload.get("nonce")
            if nonce:
                ConsumedLicenseHistory.objects.filter(nonce=nonce).update(is_active=False)

            if status == STATUS_EXPIRED and license_obj.status != STATUS_EXPIRED:
                SoftwareLicense.objects.filter(pk=license_obj.pk).update(status=STATUS_EXPIRED)
                license_obj.status = STATUS_EXPIRED

            return {
                "is_valid": False,
                "is_active": False,
                "is_trial": False,
                "is_expired": True,
                "is_lifetime": False,
                "status": STATUS_EXPIRED,
                "status_label": "Commercial License Expired",
                "plan_type": payload.get("plan", license_obj.license_type),
                "school_name": school_name,
                "school_code": school_code,
                "installation_id": license_obj.installation_id,
                "valid_until": None,
                "expires_str": payload.get("expires", "Expired"),
                "days_remaining": 0,
                "hours_remaining": 0,
                "message": msg,
                "license_obj": license_obj
            }

    # 2. Check if License was explicitly Revoked by Developer
    if license_obj.status == STATUS_REVOKED:
        return {
            "is_valid": False,
            "is_active": False,
            "is_trial": False,
            "is_expired": True,
            "is_lifetime": False,
            "status": STATUS_REVOKED,
            "status_label": "License Revoked by Developer",
            "plan_type": license_obj.license_type,
            "school_name": school_name,
            "school_code": school_code,
            "installation_id": license_obj.installation_id,
            "valid_until": None,
            "expires_str": "REVOKED",
            "days_remaining": 0,
            "hours_remaining": 0,
            "message": "Software license has been revoked by the developer.",
            "license_obj": license_obj
        }

    # 3. No commercial key -> Check 7-Day Trial Status
    trial_end = license_obj.trial_end_date
    if not trial_end:
        trial_end = license_obj.trial_start_date + datetime.timedelta(days=TRIAL_DAYS)
        SoftwareLicense.objects.filter(pk=license_obj.pk).update(trial_end_date=trial_end)


    delta = trial_end - now
    total_seconds_left = delta.total_seconds()

    if total_seconds_left > 0 and not license_obj.trial_consumed:
        # Trial is still active
        days_left = max(0, (trial_end.date() - now.date()).days)
        hours_left = int((total_seconds_left % 86400) // 3600)
        
        if license_obj.status != STATUS_TRIAL_ACTIVE:
            SoftwareLicense.objects.filter(pk=license_obj.pk).update(status=STATUS_TRIAL_ACTIVE)
            license_obj.status = STATUS_TRIAL_ACTIVE

        return {
            "is_valid": True,
            "is_active": True,
            "is_trial": True,
            "is_expired": False,
            "is_lifetime": False,
            "status": STATUS_TRIAL_ACTIVE,
            "status_label": "7-Day Trial (Active)",
            "plan_type": PLAN_TRIAL,
            "school_name": school_name,
            "school_code": school_code,
            "installation_id": license_obj.installation_id,
            "valid_until": trial_end.date(),
            "expires_str": trial_end.strftime('%Y-%m-%d %H:%M'),
            "days_remaining": days_left,
            "hours_remaining": hours_left,
            "total_seconds_remaining": total_seconds_left,
            "message": f"Trial active: {days_left}d {hours_left}h remaining.",
            "license_obj": license_obj
        }
    else:
        # Trial has expired or was consumed
        if license_obj.status != STATUS_TRIAL_EXPIRED:
            SoftwareLicense.objects.filter(pk=license_obj.pk).update(status=STATUS_TRIAL_EXPIRED, trial_consumed=True)
            license_obj.status = STATUS_TRIAL_EXPIRED

        return {
            "is_valid": False,
            "is_active": False,
            "is_trial": True,
            "is_expired": True,
            "is_lifetime": False,
            "status": STATUS_TRIAL_EXPIRED,
            "status_label": "7-Day Trial Expired",
            "plan_type": PLAN_TRIAL,
            "school_name": school_name,
            "school_code": school_code,
            "installation_id": license_obj.installation_id,
            "valid_until": trial_end.date() if trial_end else None,
            "expires_str": trial_end.strftime('%Y-%m-%d %H:%M') if trial_end else "Expired",
            "days_remaining": 0,
            "hours_remaining": 0,
            "total_seconds_remaining": 0,
            "message": "7-Day trial period has expired. Please activate with a developer license key.",
            "license_obj": license_obj
        }
