#!/usr/bin/env python3
"""
Horizon School Management System — Standalone Offline License Key Generator
Author: Software Developer / Owner
Usage:
    python license_generator.py --school-code HPS-DELHI --school-name "Horizon Public School" --days 365 --plan STANDARD
    python license_generator.py --school-code HPS-DELHI --lifetime --plan ENTERPRISE
"""

import argparse
import base64
import datetime
import hashlib
import hmac
import json
import uuid

# Must match the master secret used in Django settings or environment
DEFAULT_SIGNING_SECRET = "HORIZON_SMS_MASTER_SECURITY_KEY_2026_DEV_SECRET"

def generate_key(school_code, school_name="", days=365, is_lifetime=False, plan="STANDARD", install_id="*", max_students=0, secret=DEFAULT_SIGNING_SECRET):
    now = datetime.datetime.now(datetime.timezone.utc)
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
        "plan": str(plan).strip().upper(),
        "issued": issued_str,
        "expires": expires_str,
        "install_id": str(install_id).strip().upper() if install_id else "*",
        "max_students": int(max_students),
        "nonce": uuid.uuid4().hex[:8].upper()
    }

    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), serialized, hashlib.sha256).digest()
    
    payload_b64 = base64.urlsafe_b64encode(serialized).decode('ascii').rstrip('=')
    sig_b64 = base64.urlsafe_b64encode(sig).decode('ascii').rstrip('=')
    
    key_token = f"HRZN.{payload_b64}.{sig_b64}"
    return key_token, payload

def main():
    parser = argparse.ArgumentParser(description="Generate signed license keys for Horizon School Management System.")
    parser.add_argument("--school-code", required=True, help="School code (e.g. HPS-DELHI or *)")
    parser.add_argument("--school-name", default="", help="School official name")
    parser.add_argument("--days", type=int, default=365, help="Validity period in days (default: 365)")
    parser.add_argument("--lifetime", action="store_true", help="Issue permanent lifetime license")
    parser.add_argument("--plan", default="STANDARD", choices=["STANDARD", "PRO", "ENTERPRISE", "EXTENDED_TRIAL", "REVOKED"], help="Plan tier")
    parser.add_argument("--revoke", action="store_true", help="Generate a cryptographic revocation key (locks software)")
    parser.add_argument("--install-id", default="*", help="Lock to specific machine/installation ID (default: *)")
    parser.add_argument("--max-students", type=int, default=0, help="Max student limit (0 for unlimited)")
    parser.add_argument("--secret", default=DEFAULT_SIGNING_SECRET, help="Custom HMAC master secret if overridden in .env")

    args = parser.parse_args()
    plan_to_use = "REVOKED" if args.revoke else args.plan
    key, payload = generate_key(
        school_code=args.school_code,
        school_name=args.school_name,
        days=args.days,
        is_lifetime=args.lifetime,
        plan=plan_to_use,
        install_id=args.install_id,
        max_students=args.max_students,
        secret=args.secret
    )


    print("=" * 70)
    print("  HORIZON SOFTWARE MANAGEMENT — STANDALONE LICENSE GENERATOR")
    print("=" * 70)
    print(f"  • School Code     : {payload['sub']}")
    print(f"  • School Name     : {payload['name']}")
    print(f"  • License Plan    : {payload['plan']}")
    print(f"  • Issued Date     : {payload['issued']}")
    print(f"  • Expiration      : {payload['expires']}")
    print(f"  • Installation ID : {payload['install_id']}")
    print(f"  • Crypto Nonce    : {payload['nonce']} (1-Time Anti-Replay Guard)")
    print(f"  • Student Limit   : {'Unlimited' if args.max_students == 0 else args.max_students}")
    print("-" * 70)
    print("  GENERATED LICENSE KEY (Provide this exact key to client):")
    print(f"\n{key}\n")
    print("=" * 70)
    print("  Instructions for Developer:")
    print("  1. Copy the key above and deliver to the client school.")
    print("  2. Client enters this key into Settings (Tab 11) or Lockout Screen.")
    print("  3. Key is activated once. When expired, client cannot re-use it.")
    print("=" * 70)

if __name__ == "__main__":
    main()

