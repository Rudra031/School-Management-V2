# 🔑 Software Licensing & Activation Reference Manual

This quick reference guide covers the commercial licensing operations, cryptographic key generation, activation procedures, and license deactivation for the Horizon School Management System.

---

## 📑 Table of Contents
1. [Licensing Architecture Overview](#1-licensing-architecture-overview)
2. [Master Signing Secret](#2-master-signing-secret)
3. [Generating License Keys (CLI & Offline)](#3-generating-license-keys-cli--offline)
4. [3-Step School Activation Flow](#4-3-step-school-activation-flow)
5. [License Deactivation & Revocation (3 Ways)](#5-license-deactivation--revocation-3-ways)
6. [Anti-Replay & Anti-Tamper Protections](#6-anti-replay--anti-tamper-protections)

---

## 1. Licensing Architecture Overview

The system enforces commercial software rights using an offline-verifiable, tamper-proof **HMAC-SHA256 Cryptographic Token System**.

- **Token Structure**: `HRZN.<payload_base64>.<signature_base64>`
- **Token Claims**:
  - `v`: Schema version (default: `1`)
  - `sub`: School Code (e.g. `HPS-DELHI`)
  - `name`: School Name (e.g. `Horizon Public School`)
  - `plan`: Tier (`TRIAL`, `STANDARD`, `PREMIUM`, `ENTERPRISE`, `LIFETIME`)
  - `issued`: Date of issuance (`YYYY-MM-DD`)
  - `expires`: Expiration date (`YYYY-MM-DD` or `LIFETIME`)
  - `install_id`: Unique server hardware fingerprint (`INST-XXXX-XXXX-XXXX`)
  - `max_students`: Student capacity limit (`0` = Unlimited)
  - `nonce`: Cryptographic single-use unique random token identifier

---

## 2. Master Signing Secret

The cryptographic signature is verified against the master secret configured on the server:

```ini
# in .env or environment variable
LICENSE_SIGNING_SECRET=HORIZON_SMS_MASTER_SECURITY_KEY_2026_DEV_SECRET
```

> ⚠️ **Developer Note**: Keep this signing secret secure. Anyone with this secret can sign valid license keys.

---

## 3. Generating License Keys (CLI & Offline)

Whenever a customer provides their **School Code** and **Installation ID**:

### 1-Year Commercial License (365 Days):
```powershell
python manage.py generate_license --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --days 365 --plan STANDARD
```

### Lifetime Enterprise License:
```powershell
python manage.py generate_license --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --lifetime --plan ENTERPRISE
```

### 30-Day Extended Evaluation License:
```powershell
python manage.py generate_license --school-code HPS-DELHI --days 30 --plan EXTENDED_TRIAL
```

### Offline Generator (Run on any PC without Django running):
```powershell
python tools/license_generator.py --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --days 365 --plan STANDARD
```

---

## 4. 3-Step School Activation Flow

```text
+-------------------------------------------------------------------------+
| [ STEP 1: Copy Identity ]  -->  [ STEP 2: Send to Developer ]          |
| School Code: HPS-DELHI          Click WhatsApp / Email Generator         |
| Install ID: INST-8841-...       to send hardware machine fingerprint    |
|                                                                         |
|                                     |                                   |
|                                     v                                   |
|                          [ STEP 3: Enter Key ]                          |
|                          Paste Developer Token:                         |
|                          HRZN.eyJ2Ijox...                               |
|                          [ ⚡ Validate & Unlock ]                       |
+-------------------------------------------------------------------------+
```

1. **Step 1**: Open **Settings &rarr; Tab 11 (Software License)** or the Lockout screen.
2. **Step 2**: Click **"WhatsApp Request"** or **"Email Request"** to transmit the hardware installation fingerprint to the developer.
3. **Step 3**: Receive the signed key, paste into the activation input, and click **Validate & Activate License Key**.

---

## 5. License Deactivation & Revocation (3 Ways)

### Method 1: Instant Server Command (Direct CLI on Client Server)
```powershell
# Immediately deactivates and locks the installation
python manage.py revoke_license --reason "Subscription Non-Payment"

# Or reset back to a fresh 7-day evaluation trial
python manage.py revoke_license --reset-trial
```

### Method 2: Cryptographic Kill-Switch Key (Remote Revocation)
Generate a signed revocation key:
```powershell
python manage.py generate_license --school-code HPS-DELHI --revoke
```
When this key is pasted into the client's activation form, the system cryptographically validates the developer's signature and instantly revokes the installation.

### Method 3: Django Admin Console
Navigate to `/admin/core/softwarelicense/`, set status to `REVOKED`, and clear the `license_key` field.

---

## 6. Anti-Replay & Anti-Tamper Protections

- **One-Time Nonce Ledger (`ConsumedLicenseHistory`)**: Every activated key's UUID nonce is permanently recorded in the database. Expired or previously used keys **cannot be re-used**.
- **Clock Rollback Guard**: The system logs timestamps on each request. If the server clock is shifted backwards to bypass license expiration, the system detects tampering and locks into `STATUS_INVALID`.
- **Trial Protection**: `trial_consumed = True` ensures a client cannot continually re-trigger evaluation trial periods.
