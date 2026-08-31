# 🏫 Institutional Production Deployment & Operations Manual
### Horizon Premier Public School — Enterprise School Management ERP (CBSE / Indian School Standard)

---

## 📑 Table of Contents
1. [Prerequisites & Required Software Matrix](#1-prerequisites--required-software-matrix)
2. [System Architecture & Infrastructure Sizing](#2-system-architecture--infrastructure-sizing)
3. [Server Hardening & Firewall Setup](#3-server-hardening--firewall-setup)
4. [PostgreSQL 16 Enterprise Database Configuration](#4-postgresql-16-enterprise-database-configuration)
5. [Application Setup & Environment Configuration](#5-application-setup--environment-configuration)
6. [Process Management with Gunicorn & Systemd](#6-process-management-with-gunicorn--systemd)
7. [Nginx Reverse Proxy, Security Headers & SSL (HTTPS)](#7-nginx-reverse-proxy-security-headers--ssl-https)
8. [Initial Institutional Initialization & Role Seeding](#8-initial-institutional-initialization--role-seeding)
9. [Automated Disaster Recovery & Offsite Backups](#9-automated-disaster-recovery--offsite-backups)
10. [Zero-Downtime Application Update Workflow](#10-zero-downtime-application-update-workflow)
11. [Client / School Device Hardware & Peripherals](#11-client--school-device-hardware--peripherals)
12. [Health Checks & Troubleshooting Runbook](#12-health-checks--troubleshooting-runbook)

---

## 1. Prerequisites & Required Software Matrix

Below is the complete software inventory required for the production server, local development, and campus client workstations.

### 🖧 A. Production Server Software (Linux VPS / Dedicated Server)

| Software / Package | Minimum Version | Purpose | Installation Command |
| :--- | :--- | :--- | :--- |
| **Ubuntu Linux OS** | 22.04 LTS / 24.04 LTS | Host Operating System | Pre-installed by cloud provider (AWS, DigitalOcean, Hetzner) |
| **Python** | 3.12.x+ | Application Runtime | `sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip` |
| **PostgreSQL** | 16.x+ | Relational Enterprise Database | `sudo apt install -y postgresql postgresql-contrib libpq-dev` |
| **Nginx** | 1.24.x+ | Reverse Proxy, SSL, Static Caching | `sudo apt install -y nginx` |
| **Certbot** | 2.x+ | Automated Free SSL / HTTPS Certificates | `sudo apt install -y certbot python3-certbot-nginx` |
| **Git** | 2.40+ | Version Control & Code Deployment | `sudo apt install -y git` |
| **Build Tools (GCC)** | Standard | Compiling C-extensions (psycopg2, Pillow) | `sudo apt install -y build-essential curl` |
| **UFW & Fail2Ban** | Standard | Firewall & Intrusion Prevention | `sudo apt install -y ufw fail2ban` |
| **Docker & Compose** *(Optional)* | 24.x+ / 2.20+ | Containerized Orchestration (if using Docker) | `curl -fsSL https://get.docker.com \| sh` |

---

### 📦 B. Python Dependencies (`requirements.txt`)

These libraries are automatically installed inside the Python virtual environment:

| Python Package | Version | Purpose in School ERP |
| :--- | :--- | :--- |
| `Django` | 5.2.x+ | Core Web Framework & ORM Engine |
| `djangorestframework` | 3.15.x+ | High-Speed REST & JSON APIs (Attendance Matrix, TC Verification) |
| `reportlab` | 4.2.x+ | PDF Engine for Printable A4 Certificates, ID Cards & Report Cards |
| `openpyxl` | 3.1.x+ | Excel Export / Import for Marks Gradebooks & Student Records |
| `Pillow` | 10.3.x+ | Image Processing for Student & Staff PVC ID Card Photos |
| `django-environ` | 0.11.x+ | Secure `.env` Variable & Secrets Loader |
| `python-dateutil` | 2.9.x+ | Academic Session Dates & Attendance Calendar Math |
| `whitenoise` | 6.6.x+ | Production Static Asset Compression & Caching |
| `gunicorn` | 21.2.x+ | Multi-Worker Production WSGI Application Server |
| `psycopg2-binary` | 2.9.x+ | High-Performance PostgreSQL Database Adapter |

---

### 💻 C. Campus Client & Staff Device Requirements (School PCs, Laptops, Tablets)

No special desktop software installation is required on school computers because the ERP runs entirely in modern web browsers:

| Component | Requirement | Notes |
| :--- | :--- | :--- |
| **Web Browser** | Google Chrome 110+, MS Edge 110+, Firefox 110+, Safari 16+ | Full HTML5, CSS Glassmorphism & JavaScript support |
| **PDF Reader** | Built-in Browser PDF Viewer or Adobe Acrobat Reader | For viewing / downloading fee receipts, mark sheets, admit cards |
| **Thermal POS Printer** *(Optional)* | Standard ESC/POS 80mm or 58mm Receipt Printer | For instant Fee Counter receipts (Connects via USB) |
| **Barcode / QR Scanner** *(Optional)* | Plug-and-Play USB or Bluetooth HID Scanner | For instant student check-in, library book issue, and TC verification |
| **PVC Card Printer** *(Optional)* | Zebra, Evolis, Magicard, or Standard A4 Sheet Printer | For 8-up or single CR80 PVC identity badge printing |

---

### 🛠️ D. Local Developer Environment Software (If Developing / Testing on PC)

If running or modifying the system locally on Windows, macOS, or Linux:
1. **Python 3.12+**: [python.org/downloads](https://www.python.org/downloads/) *(Ensure "Add Python to PATH" is checked during Windows install)*.
2. **Git**: [git-scm.com](https://git-scm.com/).
3. **Code Editor**: Visual Studio Code ([code.visualstudio.com](https://code.visualstudio.com/)) with Python Extension.
4. **SQLite 3**: Pre-packaged automatically with Python for instant zero-configuration local development.

---

## 2. System Architecture & Infrastructure Sizing

```
  [Internet / School Campus / Parents]
      │
      ▼ (Port 443 HTTPS)
  ┌─────────────────────────────────────────────────────────────┐
  │ NGINX Reverse Proxy (SSL Termination, Caching, Rate Limit)  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼ (Static/Media)                ▼ (Dynamic WSGI :8000)
       ┌──────────────────┐           ┌────────────────────────────────┐
       │ /staticfiles/    │           │ Gunicorn WSGI Workers          │
       │ /media/ (Uploads)│           │ (Python 3.12 • Django 5.2 Core)│
       └──────────────────┘           └──────────────┬─────────────────┘
                                                     │
                                                     ▼
                                      ┌────────────────────────────────┐
                                      │ PostgreSQL 16 Enterprise DB    │
                                      │ (horizon_school_db)            │
                                      └────────────────────────────────┘
```

### Hardware Sizing Matrix

| School Scale | Students Enrolled | Recommended VM Spec | Monthly Est. Cost | Recommended Cloud |
| :--- | :--- | :--- | :--- | :--- |
| **Standard School** | Up to 1,500 | 2 vCPU, 4 GB RAM, 60 GB NVMe | \$12 – \$20 / mo | DigitalOcean / Hetzner / AWS Lightsail |
| **Large Campus** | 1,500 – 4,000 | 4 vCPU, 8 GB RAM, 120 GB NVMe | \$30 – \$50 / mo | AWS EC2 (t4g.xlarge) / Linode |
| **Multi-Branch / Trust** | 4,000 – 12,000+ | 8 vCPU, 16 GB RAM, 250 GB NVMe | \$80 – \$120 / mo | Dedicated Server / AWS RDS + EC2 |

---

## 3. Server Hardening & Firewall Setup

Connect to your freshly provisioned Linux server as `root`:

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install all required system software in 1 command
sudo apt install -y build-essential curl git ufw fail2ban python3.12 python3.12-venv python3.12-dev libpq-dev postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# 3. Create non-root deployer user
sudo adduser --gecos "" deployer
sudo usermod -aG sudo deployer

# 4. Configure UFW Firewall (Only allow SSH, HTTP, HTTPS)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 5. Enable Fail2Ban against brute force attacks
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 4. PostgreSQL 16 Enterprise Database Configuration

```bash
# Switch to postgres superuser
sudo -u postgres psql
```

Execute the following SQL commands:

```sql
-- 1. Create dedicated database
CREATE DATABASE horizon_school_db;

-- 2. Create restricted application user with strong password
CREATE USER horizon_admin WITH ENCRYPTED PASSWORD 'ChangeThisToASecureRandomPassword2026!';

-- 3. Configure production session parameters
ALTER ROLE horizon_admin SET client_encoding TO 'utf8';
ALTER ROLE horizon_admin SET default_transaction_isolation TO 'read committed';
ALTER ROLE horizon_admin SET timezone TO 'Asia/Kolkata';

-- 4. Grant privileges
GRANT ALL PRIVILEGES ON DATABASE horizon_school_db TO horizon_admin;
GRANT ALL ON SCHEMA public TO horizon_admin;

\q
```

---

## 5. Application Setup & Environment Configuration

### 5.1 Clone Repository & Virtual Environment
```bash
# Create directory
sudo mkdir -p /var/www/school_management
sudo chown -R deployer:www-data /var/www/school_management
sudo chmod -R 775 /var/www/school_management

# Switch to deployer user
su - deployer
cd /var/www/school_management

# Clone codebase
git clone <YOUR_GIT_REPOSITORY_URL> .

# Setup Python 3.12 virtualenv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 5.2 Create Production Environment File (`.env`)
```bash
cp .env.example .env
nano .env
```

Ensure `.env` contains the following production variables:

```env
DEBUG=False
SECRET_KEY=django-secure-prod-key-kjas897234h98sdf987y234khjsdf897234kjh
ALLOWED_HOSTS=school.edu.in,www.school.edu.in,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://school.edu.in,https://www.school.edu.in

# SSL & Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Database
DB_ENGINE=postgresql
DB_NAME=horizon_school_db
DB_USER=horizon_admin
DB_PASSWORD=ChangeThisToASecureRandomPassword2026!
DB_HOST=localhost
DB_PORT=5432

# School Details
DEFAULT_SCHOOL_NAME="Horizon Premier Public School"
DEFAULT_SCHOOL_AFFILIATION="Affiliated to CBSE, New Delhi (Affiliation No. 2430089 | School Code: 15614)"
DEFAULT_SCHOOL_ADDRESS="Sector 14, Urban Estate, Rohini, New Delhi - 110085"
DEFAULT_SCHOOL_PHONE="+91 (011) 2748-9012 / +91 98765 43210"
DEFAULT_TIMEZONE=Asia/Kolkata
DEFAULT_CURRENCY_SYMBOL=₹
DEFAULT_CURRENCY_CODE=INR
DEFAULT_ATTENDANCE_THRESHOLD=75.0
```

### 5.3 Database Migrations & Static Asset Compilation
```bash
# Apply database schemas
python manage.py migrate

# Compile and compress static files via WhiteNoise
python manage.py collectstatic --noinput

# Set proper permissions on uploads directory
mkdir -p media staticfiles
sudo chown -R deployer:www-data media staticfiles
sudo chmod -R 775 media staticfiles
```

---

## 6. Process Management with Gunicorn & Systemd

Create the Systemd service file:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Paste the following configuration:

```ini
[Unit]
Description=Gunicorn WSGI Application Server for Horizon School ERP
After=network.target postgresql.service

[Service]
User=deployer
Group=www-data
WorkingDirectory=/var/www/school_management
ExecStart=/var/www/school_management/venv/bin/gunicorn           --config /var/www/school_management/gunicorn.conf.py           config.wsgi:application
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=30
PrivateTmp=true

# Security sandbox
ProtectSystem=full
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
```

Enable and start Gunicorn:
```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# Verify status (should show active (running))
sudo systemctl status gunicorn
```

---

## 7. Nginx Reverse Proxy, Security Headers & SSL (HTTPS)

### 7.1 Create Nginx Site Configuration
```bash
sudo nano /etc/nginx/sites-available/school_management
```

Paste the following configuration:

```nginx
upstream django_cluster {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name school.edu.in www.school.edu.in;
    client_max_body_size 50M;

    # Gzip Compression for fast page loading
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
    gzip_min_length 1000;

    # Static Assets (Served directly by Nginx with 30-day browser caching)
    location /static/ {
        alias /var/www/school_management/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }

    # Uploaded Media (Student Photos, TC Proofs, Circulars)
    location /media/ {
        alias /var/www/school_management/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Certbot ACME Challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Dynamic Django Application
    location / {
        proxy_pass http://django_cluster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
```

### 7.2 Activate Site and Test
```bash
sudo ln -sf /etc/nginx/sites-available/school_management /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 7.3 Install Free SSL Certificate via Let's Encrypt
```bash
sudo certbot --nginx -d school.edu.in -d www.school.edu.in --non-interactive --agree-tos -m admin@school.edu.in --redirect
```

---

## 8. Initial Institutional Initialization & Role Seeding

Create the Master Superadministrator Account:

```bash
cd /var/www/school_management
source venv/bin/activate

# Interactive superuser creation
python manage.py createsuperuser
```

Enter:
- **Email**: `admin@school.edu.in`
- **First Name**: `Principal`
- **Last Name**: `Office`
- **Password**: `SecureAdminPassword2026!`

### Initial School Setup via Web Portal
1. Open `https://school.edu.in/accounts/login/` in browser.
2. Sign in with the superadmin account.
3. Go to **Academic Setup** $ightarrow$ **Academic Years** $ightarrow$ Set `2026-2027` as **Active**.
4. Go to **Academic Setup** $ightarrow$ **Classes & Sections** $ightarrow$ Initialize Nursery to Class XII.
5. Go to **Fee Regulation** $ightarrow$ **Fee Structures** $ightarrow$ Set monthly tuition and admission fee heads.

---

## 9. Automated Disaster Recovery & Offsite Backups

Create the automated daily database backup script:

```bash
sudo mkdir -p /var/backups/school_erp
sudo nano /usr/local/bin/backup_school_erp.sh
```

Paste the following script:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/school_erp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Dump and compress PostgreSQL database
PGPASSWORD="ChangeThisToASecureRandomPassword2026!" pg_dump -U horizon_admin -h localhost horizon_school_db | gzip > "$FILENAME"

# Retain only last 30 days of backups locally
find "$BACKUP_DIR" -type f -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Database backup completed successfully: $FILENAME"
```

Make executable and add to crontab:

```bash
sudo chmod +x /usr/local/bin/backup_school_erp.sh

# Add crontab job to run every night at 2:00 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_school_erp.sh >> /var/log/school_backup.log 2>&1") | crontab -
```

---

## 10. Zero-Downtime Application Update Workflow

Create an update script `/var/www/school_management/deploy.sh`:

```bash
nano /var/www/school_management/deploy.sh
```

Paste:

```bash
#!/bin/bash
set -e
echo "Starting School ERP Update..."

cd /var/www/school_management
source venv/bin/activate

# 1. Pull latest verified changes from git
git pull origin main

# 2. Update dependencies
pip install -r requirements.txt

# 3. Apply schema migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Gracefully reload Gunicorn workers with 0 downtime
sudo systemctl reload gunicorn

echo "✅ School ERP successfully updated and live!"
```

Make executable:
```bash
chmod +x /var/www/school_management/deploy.sh
```

---

## 11. Client / School Device Hardware & Peripherals

| Equipment | Supported Standard | Recommended Models / Specs | Driver Needed? |
| :--- | :--- | :--- | :--- |
| **School Computers** | Windows 10/11, macOS, ChromeOS, Ubuntu | Intel Core i3 / Ryzen 3, 4GB RAM+ | No (Browser-based) |
| **POS Thermal Printer** | ESC/POS (80mm / 58mm) | TVS RP3200, EPSON TM-T82, Xprinter | Standard USB Vendor Driver |
| **Barcode Scanner** | USB / Bluetooth HID (1D / 2D QR) | Honeywell Voyager, TVS BSC 101, Inateck | No (Plug & Play HID) |
| **PVC Card Printer** | CR-80 Standard ID (85.6 × 54 mm) | Zebra ZC300, Evolis Zenius, Magicard 300 | Standard USB Vendor Driver |

---

## 12. Health Checks & Troubleshooting Runbook

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **502 Bad Gateway** | Gunicorn service is stopped or crashed. | Run `sudo systemctl status gunicorn` and check logs with `journalctl -u gunicorn -e`. |
| **CSRF Verification Failed** | Missing domain in `CSRF_TRUSTED_ORIGINS`. | Add your exact domain (e.g. `https://school.edu.in`) to `CSRF_TRUSTED_ORIGINS` in `.env`. |
| **Images / Photos not uploading** | Permission error on `media/` directory. | Run `sudo chown -R deployer:www-data /var/www/school_management/media/ && sudo chmod -R 775 media/`. |
| **Database Connection Refused** | PostgreSQL service stopped. | Run `sudo systemctl restart postgresql`. |
| **Static styling missing** | Static assets not collected. | Run `python manage.py collectstatic --noinput`. |

---

*Horizon School ERP is engineered, hardened, and verified for institutional 24/7 reliability.*
