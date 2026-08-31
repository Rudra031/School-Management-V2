# 📚 Horizon School Management System — Documentation Center

Welcome to the official documentation directory for **Horizon School Management & Administration System (SMS)**.

---

## 📑 Available Documentation & Manuals

| Document | Target Audience | Summary & Key Topics Covered |
| :--- | :--- | :--- |
| 📖 [**User Guide (`USER_GUIDE.md`)**](USER_GUIDE.md) | School Administrators, Principals, Faculty, Accountants, Parents & Students | Visual workflows, UI mockups, Demo Fast-Fill logins, Dual Admissions pipeline (Quick vs Full), Attendance Matrix, Fee Invoicing, Exams & Gradebooks, Timetables, and Library Circulation. |
| 🛠️ [**Developer Guide (`DEVELOPER_GUIDE.md`)**](DEVELOPER_GUIDE.md) | Software Developers, Maintainers & SaaS Vendors | Technical architecture, 18-app modular breakdown, test suite, HMAC-SHA256 cryptographic licensing engine, anti-replay nonce ledger, clock rollback protection, and database factory reset. |
| 🚀 [**Deployment Guide (`DEPLOYMENT_GUIDE.md`)**](DEPLOYMENT_GUIDE.md) | DevOps Engineers, System Admins & IT Staff | Enterprise Linux (Ubuntu 22/24) deployment, PostgreSQL 16 setup, Gunicorn systemd daemon, Nginx reverse proxy, Certbot SSL/TLS, and automated backup schedules. |
| 🎓 [**Admissions Guide (`ADMISSIONS_GUIDE.md`)**](ADMISSIONS_GUIDE.md) | Admission Officers & Registrars | Detailed guide on the Quick Admission fast-track, instant conversion, continuation into the 10-step dossier, document uploads (TC, marksheets), and printable admission letters. |

---

## 🏛 System Layout Map

```text
school_management/
├── docs/                       # 📚 Central Documentation Folder
│   ├── README.md               # Documentation Index (this file)
│   ├── USER_GUIDE.md           # School User & Staff Manual
│   ├── DEVELOPER_GUIDE.md      # Developer & Vendor Control Manual
│   ├── DEPLOYMENT_GUIDE.md     # Production Deployment Runbook
│   ├── LICENSING_GUIDE.md      # Licensing & Key Generation Reference
│   └── ADMISSIONS_GUIDE.md     # Admissions Pipeline Guide
├── core/                       # Core system, licensing, audit logs
├── accounts/                   # RBAC authentication & dashboard routing
├── academics/                  # Classes, sections, subjects, academic years
├── students/                   # Permanent student SIS records
├── staff/                      # Staff & faculty directory
├── parents/                    # Multi-child parent portal
├── admissions/                 # Dual admissions pipeline
├── attendance/                 # Attendance register matrix
├── fees/                       # Fee invoicing, receipts, ledger
├── examinations/               # Exams, grading scale, report cards
├── timetable/                  # Timetable generator
├── library/                    # Catalog, barcode loans, fines
├── documents/                  # Document storage repository
├── inventory/                  # Asset management & custody
├── expenses/                   # Operating expense vouchers
├── reports/                    # Reports hub & analytics
├── website/                    # School marketing homepage
├── tools/                      # Standalone developer utilities
├── templates/                  # Frontend UI templates
└── README.md                   # Project Root Overview
```
