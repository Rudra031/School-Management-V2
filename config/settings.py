import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env manually to avoid external dependency issues
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-sms-modern-enterprise-school-management-secret-key-2026')
LICENSE_SIGNING_SECRET = os.environ.get('LICENSE_SIGNING_SECRET', 'HORIZON_SMS_MASTER_SECURITY_KEY_2026_DEV_SECRET')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '*').split(',') if host.strip()]

# CSRF Trusted Origins (Domains allowed for Form & API Submissions in Production)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1,http://localhost').split(',') if origin.strip()]

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

LOCAL_APPS = [
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'academics.apps.AcademicsConfig',
    'staff.apps.StaffConfig',
    'students.apps.StudentsConfig',
    'parents.apps.ParentsConfig',
    'timetable.apps.TimetableConfig',
    'attendance.apps.AttendanceConfig',
    'examinations.apps.ExaminationsConfig',
    'assignments.apps.AssignmentsConfig',
    'fees.apps.FeesConfig',
    'library.apps.LibraryConfig',
    'admissions.apps.AdmissionsConfig',
    'communication.apps.CommunicationConfig',
    'documents.apps.DocumentsConfig',
    'leave.apps.LeaveConfig',
    'inventory.apps.InventoryConfig',
    'expenses.apps.ExpensesConfig',
    'reports.apps.ReportsConfig',
    'website.apps.WebsiteConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]

# Register WhiteNoise for production static file serving if installed
try:
    import whitenoise
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
except ImportError:
    pass

MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditLogMiddleware',
    'core.middleware.ActiveAcademicYearMiddleware',
    'core.middleware.SoftwareLicenseMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.school_settings',
                'core.context_processors.active_academic_year',
                'core.context_processors.unread_notifications',
                'core.context_processors.just_logged_in_splash',
                'core.context_processors.license_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration (supports PostgreSQL, MySQL, SQLite)
db_engine = os.environ.get('DB_ENGINE', 'sqlite3').lower()
if db_engine in ('postgresql', 'postgres', 'psycopg2'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'school_erp'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
elif db_engine in ('mysql', 'mariadb'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'school_erp'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / os.environ.get('DB_NAME', 'db.sqlite3'),
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization & Indian School ERP Localization
LANGUAGE_CODE = 'en-in'
TIME_ZONE = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Kolkata')
USE_I18N = True
USE_TZ = True

# Institutional Defaults (Indian School System)
CURRENCY_CODE = os.environ.get('DEFAULT_CURRENCY_CODE', 'INR')
CURRENCY_SYMBOL = os.environ.get('DEFAULT_CURRENCY_SYMBOL', '₹')
DEFAULT_SCHOOL_NAME = os.environ.get('DEFAULT_SCHOOL_NAME', 'Horizon Premier Public School')
DEFAULT_SCHOOL_AFFILIATION = os.environ.get('DEFAULT_SCHOOL_AFFILIATION', 'Affiliated to CBSE, New Delhi (Affiliation No. 2430089)')
DEFAULT_SCHOOL_ADDRESS = os.environ.get('DEFAULT_SCHOOL_ADDRESS', 'Sector 14, Urban Estate, Rohini, New Delhi - 110085')
DEFAULT_SCHOOL_PHONE = os.environ.get('DEFAULT_SCHOOL_PHONE', '+91 (011) 2748-9012 / +91 98765 43210')
DEFAULT_ATTENDANCE_THRESHOLD = float(os.environ.get('DEFAULT_ATTENDANCE_THRESHOLD', '75.0'))

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Static file storage (uses WhiteNoise in production if available)
try:
    import whitenoise
    static_storage = 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'
except ImportError:
    static_storage = 'django.contrib.staticfiles.storage.StaticFilesStorage'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': static_storage,
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard_router'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Django Messages Bootstrap Tags
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

# Allow same-origin iframes for No-Code Visual Studio Customizer
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Production Security Headers & SSL Hardening
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    if os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1'):
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
