# 🛠️ Horizon School Management System — Complete Developer & Vendor Guide

A comprehensive architectural and operational manual for software developers and vendors deploying, maintaining, and controlling Horizon SMS installations.

---

## 📑 Table of Contents
1. [Architecture & Tech Stack](#1-architecture--tech-stack)
2. [Project Directory Layout](#2-project-directory-layout)
3. [Local Development & Setup](#3-local-development--setup)
4. [Database Seeding & Automated Tests](#4-database-seeding--automated-tests)
5. [Software Licensing & Monetization Engine](#5-software-licensing--monetization-engine)
6. [Generating License Keys (CLI & Offline Script)](#6-generating-license-keys-cli--offline-script)
7. [Deactivating & Revoking Licenses (3 Methods)](#7-deactivating--revoking-licenses-3-methods)
8. [Anti-Replay Nonce Ledger & Clock Tamper Guard](#8-anti-replay-nonce-ledger--clock-tamper-guard)
9. [Database Factory Reset & Data Sanitization](#9-database-factory-reset--data-sanitization)
10. [Production Deployment & DevOps](#10-production-deployment--devops)

---

## 1. Architecture & Tech Stack

- **Backend Framework**: Python 3.12+ & Django 5.2+ (Clean MVT + Model Backends).
- **Authentication**: `accounts.backends.EmailOrUsernameModelBackend` (Supports Case-Insensitive Email or Username).
- **Frontend Architecture**: Server-Rendered Django Templates + Bootstrap 5 + Vanilla JS + FontAwesome 6 + Chart.js.
- **Database**: SQLite3 (Development / Single-Node) & PostgreSQL 16+ (Production).
- **Security Engine**: HMAC-SHA256 Cryptographic Licensing Tokenizer (`core.licensing`).

---

## 2. Project Directory Layout

```text
school_management/
├── docs/                    # 📚 Central Documentation Folder
├── config/                  # Django project root (settings.py, urls.py, wsgi.py)
├── core/                    # Core singleton models, licensing engine, audit logs, permissions
│   ├── licensing.py         # HMAC-SHA256 token generator & validator
│   ├── middleware.py        # SoftwareLicenseMiddleware & Audit logging middleware
│   └── management/commands/ # CLI commands (generate_license, revoke_license, seed_demo_data)
├── accounts/                # 9-Role RBAC user model, dashboard routing, auth forms
├── academics/               # Academic years, class levels, sections, subjects
├── students/                # Permanent student profiles, enrollment bridge, medical records
├── teachers/                # Faculty profiles, departmental designations
├── parents/                 # Parent profiles, multi-child switcher
├── admissions/              # Dual admissions pipeline (Quick + 10-step full dossier)
├── attendance/              # Attendance matrix, low-attendance alerts (<75%)
├── fees/                    # Fee structures, student invoicing, thermal receipts
├── examinations/            # GPA/Letter grade scales, report card generation
├── timetable/               # Collision-free schedule generator
├── library/                 # Book catalog, ISBN barcode scanner, circulation
├── documents/               # Role-tiered document repository
├── communication/           # Notices, circulars, SMS/Email hooks
├── inventory/               # Asset custody, valuation, stock alerts
├── reports/                 # Executive reporting and demographic analytics
├── website/                 # Public school marketing homepage & online inquiry forms
├── tools/                   # Standalone developer utilities
│   └── license_generator.py # Standalone offline license generator
├── templates/               # Modular UI templates (Glassmorphism & SaaS dark/light)
├── static/                  # CSS stylesheets, JS bundles, branding assets
└── README.md                # Main Project Overview
```

---

## 3. Local Development & Setup

### Clone & Virtual Environment:
```powershell
# Navigate to project directory
cd d:\school_management

# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### Apply Migrations:
```powershell
python manage.py migrate
```

### Run Server:
```powershell
python manage.py runserver 127.0.0.1:8000
```

---

## 4. Database Seeding & Automated Tests

### Seed Rich Demonstration Dataset:
Seeds 6 standard `@school.edu` fast-fill personas and `@horizonacademy.edu` accounts with password `Password@123`:
```powershell
python manage.py seed_demo_data
```

### Run Full Test Suite across All 18 Apps:
```powershell
python manage.py test core accounts admissions website documents
```
> Current Test Suite Status: **58/58 Tests Passing (100% OK)**

---

## 5. Software Licensing & Monetization Engine

The software is protected by a **Cryptographic HMAC-SHA256 Licensing Engine** located in `core/licensing.py`.

### Architectural Model:
```text
  Key Format: HRZN.<base64_json_payload>.<base64_hmac_sha256_signature>
```

### Token Payload Structure:
```json
{
  "v": 1,
  "sub": "HPS-DELHI",
  "name": "Horizon Public School",
  "plan": "STANDARD",
  "issued": "2026-08-31",
  "expires": "2027-08-31",
  "install_id": "INST-8841-EC45-0715",
  "max_students": 0,
  "nonce": "AD558AFD3EC4"
}
```

### Master Signing Secret:
Set `LICENSE_SIGNING_SECRET` in your environment or `.env`:
```ini
LICENSE_SIGNING_SECRET=YOUR_SECURE_MASTER_HMAC_SECRET_STRING_2026
```

---

## 6. Generating License Keys (CLI & Offline Script)

Whenever a client school sends you their **School Code** and **Installation ID**:

### Method A: Django Management Command
```powershell
# 1-Year Commercial License (365 Days)
python manage.py generate_license --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --days 365 --plan STANDARD

# Permanent Lifetime Enterprise License
python manage.py generate_license --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --lifetime --plan ENTERPRISE

# 30-Day Evaluation Extension
python manage.py generate_license --school-code HPS-DELHI --days 30 --plan EXTENDED_TRIAL
```

### Method B: Standalone Offline Generator (Run from any laptop)
```powershell
python tools/license_generator.py --school-code HPS-DELHI --school-name "Horizon Public School" --install-id INST-8841-EC45-0715 --days 365 --plan STANDARD
```

---

## 7. Deactivating & Revoking Licenses (3 Methods)

### Method 1: Instant Server Command (Direct CLI on Server)
```powershell
# Instantly Revoke and Lock the Installation
python manage.py revoke_license --reason "Subscription Expired / Non-Payment"

# Or Reset back to a fresh 7-Day Evaluation Trial
python manage.py revoke_license --reset-trial
```

### Method 2: Cryptographic Kill-Switch Key (Remote / Offline Revocation)
Generate a signed revocation key to deliver to the client server:
```powershell
python manage.py generate_license --school-code HPS-DELHI --revoke
```
When this key is pasted into the activation box, the system cryptographically verifies the developer signature and locks the software immediately.

### Method 3: Django Admin Portal
Go to `/admin/core/softwarelicense/`, set status to `REVOKED`, and clear the `license_key` field.

---

## 8. Anti-Replay Nonce Ledger & Clock Tamper Guard

1. **One-Time Nonce Ledger (`ConsumedLicenseHistory`)**:
   - Each license key has a cryptographic UUID `nonce`.
   - When activated, its nonce is permanently logged.
   - **Clients CANNOT re-use or re-activate old/expired license keys.**
2. **Clock Rollback Tamper Protection**:
   - Tracks `last_system_time` on the server.
   - If server clock is wound back to bypass expiration, the system detects tampering and locks into `STATUS_INVALID`.
3. **Trial Anti-Reset**:
   - `trial_consumed = True` ensures clients cannot reset the 7-day evaluation trial.

---

## 9. Database Factory Reset & Data Sanitization

Located in **Settings &rarr; Tab 10 (Factory Reset)**:
- Requires Superadmin authentication password + Confirmation phrase `RESET-CONFIRM`.
- Purges transactional data (Students, Admissions, Invoices, Attendance, Exams).
- Preserves master administrative user accounts and system configuration parameters.

---

## 10. Production Deployment & DevOps

### Production Environment Variables (`.env`):
```ini
DEBUG=False
SECRET_KEY=your-production-django-secret-key-here
LICENSE_SIGNING_SECRET=your-developer-hmac-master-secret
ALLOWED_HOSTS=school.yourdomain.com,127.0.0.1
DATABASE_URL=postgresql://sms_user:sms_pass@localhost:5432/horizon_sms
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Systemd Service Setup (Linux/Gunicorn):
```ini
[Unit]
Description=Horizon School Management Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/school_management
ExecStart=/var/www/school_management/venv/bin/gunicorn --access-logfile - --workers 4 --bind unix:/run/horizon_sms.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy:
```nginx
server {
    listen 80;
    server_name school.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name school.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/school.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/school.yourdomain.com/privkey.pem;

    location /static/ {
        alias /var/www/school_management/staticfiles/;
    }

    location /media/ {
        alias /var/www/school_management/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/horizon_sms.sock;
    }
}
```
