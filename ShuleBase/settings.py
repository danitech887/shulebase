"""
Django settings for ShuleBase project.
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Security
# =========================
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# =========================
# Custom User
# =========================
AUTH_USER_MODEL = 'Pupils.Users'

# =========================
# Installed Apps
# =========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'Dashboard',
    'Pupils',
]

# =========================
# Middleware
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================
# Auth
# =========================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/pupil/dashboard/'

AUTHENTICATION_BACKENDS = [
    'Pupils.utils.per_school_auth_backend.PerSchoolDBBackend',
]

# =========================
# URLs / Templates
# =========================
ROOT_URLCONF = 'ShuleBase.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR,'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Pupils.context_processors.current_school',
            ],
        },
    },
]

WSGI_APPLICATION = 'ShuleBase.wsgi.application'

# =========================
# Database
# =========================
if os.getenv("RENDER"):  # Render sets this environment variable
    DATABASES = {
        "default": dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "ShuleBase"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", "daenicel"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "3306"),
        }
    }


# =========================
# Password Validation
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================
# Email
# =========================
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'shulebasesoftware@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'wbuncdlrrhdbioco')
DEFAULT_FROM_EMAIL = f"ShuleBase <{EMAIL_HOST_USER}>"

# Fallback to console backend if no SMTP creds provided (useful in dev)
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =========================
# Internationalization
# =========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# =========================
# Static & Media
# =========================
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security headers for production
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    CSRF_TRUSTED_ORIGINS_ENV = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
    if CSRF_TRUSTED_ORIGINS_ENV:
        CSRF_TRUSTED_ORIGINS = [o.strip() for o in CSRF_TRUSTED_ORIGINS_ENV.split(',') if o.strip()]

# =========================
# Default Auto Field
# =========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'





"""
Django settings for ShuleBase project (Localhost / Development)
# """

# from pathlib import Path
# import os

# BASE_DIR = Path(__file__).resolve().parent.parent

# # # =========================
# # # Security
# # # =========================
# SECRET_KEY = 'django-insecure-w!e3mp!16)rz+1q2(pa_koy2gvvh2gp)5oo3m5+5_aki%xu%q2'  # Use any random string in dev
# DEBUG = True
# ALLOWED_HOSTS = ['localhost','127.0.0.1','10.10.19.5']  # Localhost only

# # # =========================
# # # Custom User
# # # =========================
# AUTH_USER_MODEL = 'Pupils.Users'

# # # =========================
# # # Installed Apps
# # # =========================
# INSTALLED_APPS = [
#      'django.contrib.admin',
#      'django.contrib.auth',
#      'django.contrib.contenttypes',
#      'django.contrib.sessions',
#      'django.contrib.messages',
#      'django.contrib.staticfiles',

#     #   Local apps
#      'Dashboard',
#      'Pupils',
#  ]

# # # =========================
# # # Middleware
# # # =========================
# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     "whitenoise.middleware.WhiteNoiseMiddleware", 
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# # # =========================
# # # Auth
# # # =========================
# LOGIN_URL = '/login/'
# LOGIN_REDIRECT_URL = '/pupil/dashboard/'

# AUTHENTICATION_BACKENDS = [
#     'Pupils.utils.per_school_auth_backend.PerSchoolDBBackend',
# ]

# # # =========================
# # # URLs / Templates
# # # =========================
# ROOT_URLCONF = 'ShuleBase.urls'

# TEMPLATES = [
#      {
#          'BACKEND': 'django.template.backends.django.DjangoTemplates',
#          'DIRS': [os.path.join(BASE_DIR, 'templates')],
#          'APP_DIRS': True,
#          'OPTIONS': {
#              'context_processors': [
#                  'django.template.context_processors.debug',
#                  'django.template.context_processors.request',
#                  'django.contrib.auth.context_processors.auth',
#                  'django.contrib.messages.context_processors.messages',
#                  'Pupils.context_processors.current_school',
#              ],
#          },
#      },
#  ]

# WSGI_APPLICATION = 'ShuleBase.wsgi.application'

# # # =========================
# # # Database (Local MySQL)
# # # =========================
# DATABASES = {
#      "default": {
#          "ENGINE": "django.db.backends.mysql",
#          "NAME": "ShuleBase",
#          "USER": "root",
#          "PASSWORD": "daenicel",  # your local MySQL password
#          "HOST": "localhost",
#          "PORT": "3306",
#      }
#  }

# # # =========================
# # # Password Validation
# # # =========================
# AUTH_PASSWORD_VALIDATORS = [
#      {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
#      {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
#      {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
#      {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
# ]

# # # =========================
# # # Email (console for dev)
# # # =========================
# # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# # # =========================
# # # Internationalization
# # # =========================
# LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'Africa/Nairobi'
# USE_I18N = True
# USE_TZ = True

# # # =========================
# # # Static & Media
# # # =========================
# STATIC_URL = 'static/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# # # =========================
# # # Default Auto Field
# # # =========================
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

