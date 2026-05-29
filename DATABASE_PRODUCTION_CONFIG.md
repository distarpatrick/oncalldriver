"""
Production Database Configuration
Add to your E_marketing/settings.py for production environment
"""

# ============================================================================

# PART 1: PRODUCTION DATABASE SETTINGS

# ============================================================================

"""
SWITCH FROM SQLite TO POSTGRESQL FOR PRODUCTION
SQLite is only suitable for development/testing!

For Production:

1. Upgrade to PostgreSQL (recommended)
2. Or MySQL (alternative)

Install:
pip install psycopg2-binary # For PostgreSQL

Update DATABASES:
"""

# ============================================================================

# OPTION A: PostgreSQL Configuration (RECOMMENDED)

# ============================================================================

DATABASES_POSTGRESQL = {
'default': {
'ENGINE': 'django.db.backends.postgresql',
'NAME': 'on_call_driver_db', # Database name
'USER': 'postgres', # DB user
'PASSWORD': 'your-password', # DB password
'HOST': 'localhost', # Or your DB server IP
'PORT': '5432', # PostgreSQL port

        # Connection pooling (handle concurrent connections)
        'CONN_MAX_AGE': 600,                   # Keep alive for 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,             # Connection timeout
            'options': '-c default_transaction_isolation=read_committed',
        }
    }

}

# ============================================================================

# OPTION B: MySQL Configuration (Alternative)

# ============================================================================

DATABASES_MYSQL = {
'default': {
'ENGINE': 'django.db.backends.mysql',
'NAME': 'on_call_driver_db',
'USER': 'root',
'PASSWORD': 'your-password',
'HOST': 'localhost',
'PORT': '3306',

        'OPTIONS': {
            'charset': 'utf8mb4',
            'use_unicode': True,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'autocommit': True,
            'connect_timeout': 10,
        }
    }

}

# ============================================================================

# PART 2: CACHING CONFIGURATION (Redis)

# ============================================================================

"""
Install Redis: # Ubuntu/Debian
sudo apt-get install redis-server

    # macOS
    brew install redis

    # Windows - use Docker or Windows Subsystem for Linux

Install Django Redis:
pip install django-redis
"""

CACHES = {
'default': {
'BACKEND': 'django_redis.cache.RedisCache',
'LOCATION': 'redis://127.0.0.1:6379/1', # Redis instance

        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,           # Max concurrent connections
                'health_check_interval': 30,     # Health check every 30 seconds
            },
            'SOCKET_CONNECT_TIMEOUT': 5,         # Connection timeout
            'SOCKET_TIMEOUT': 5,                 # Request timeout
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',  # Compression
            'IGNORE_EXCEPTIONS': True,           # Don't crash if Redis is down
        }
    }

}

# ============================================================================

# PART 3: SESSION CONFIGURATION

# ============================================================================

# Use Redis for sessions (faster than database)

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Session timeout

SESSION_COOKIE_AGE = 86400 # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Secure session cookies

SESSION_COOKIE_SECURE = True # HTTPS only
SESSION_COOKIE_HTTPONLY = True # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict' # CSRF protection

# ============================================================================

# PART 4: DATABASE QUERY OPTIMIZATION SETTINGS

# ============================================================================

# Enable query logging in development

if DEBUG:
LOGGING = {
'version': 1,
'disable_existing_loggers': False,
'handlers': {
'console': {
'class': 'logging.StreamHandler',
},
'file': {
'class': 'logging.FileHandler',
'filename': BASE_DIR / 'logs/database.log',
},
},
'loggers': {
'django.db.backends': {
'handlers': ['console', 'file'],
'level': 'DEBUG',
'propagate': False,
},
},
}

# ============================================================================

# PART 5: ATOMIC TRANSACTIONS & CONNECTION POOLING

# ============================================================================

# Use atomic transactions for data consistency

ATOMIC_REQUESTS = False # Set to True for full-page transactions (slower)

# For high-traffic scenarios, increase connection pool size

if not DEBUG:
DATABASES['default']['CONN_MAX_AGE'] = 600 # Keep connections alive
DATABASES['default']['OPTIONS']['connect_timeout'] = 30

# ============================================================================

# PART 6: SECURITY HARDENING

# ============================================================================

# Database-level security

if not DEBUG: # Enforce HTTPS
SECURE_SSL_REDIRECT = True

    # Security headers
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # CSRF protection
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True

    # Content Security Policy
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ("'self'",),
        'script-src': ("'self'", "'unsafe-inline'"),
        'style-src': ("'self'", "'unsafe-inline'"),
        'img-src': ("'self'", 'data:', 'https:'),
    }

# ============================================================================

# PART 7: ALLOWED HOSTS (Production)

# ============================================================================

ALLOWED_HOSTS = [
'your-domain.com',
'www.your-domain.com',
'api.your-domain.com',
'192.168.1.100', # Internal IP (if needed)
]

# ============================================================================

# PART 8: RATE LIMITING (Prevent abuse)

# ============================================================================

"""
Install django-ratelimit:
pip install django-ratelimit

Usage in views:
from django_ratelimit.decorators import ratelimit

    @ratelimit(key='ip', rate='100/h')  # 100 requests per hour per IP
    def book_car(request):
        ...

"""

# ============================================================================

# PART 9: DATABASE BACKUPS

# ============================================================================

"""
Create backup script: backup_database.sh

For PostgreSQL:
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d\_%H%M%S")

    pg_dump -U postgres on_call_driver_db | \
        gzip > /backups/on_call_driver_db_$TIMESTAMP.sql.gz

    # Keep only last 30 days
    find /backups -name "*.sql.gz" -mtime +30 -delete

For MySQL:
#!/bin/bash
TIMESTAMP=$(date +"%Y%m%d\_%H%M%S")

    mysqldump -u root -p on_call_driver_db | \
        gzip > /backups/on_call_driver_db_$TIMESTAMP.sql.gz

    find /backups -name "*.sql.gz" -mtime +30 -delete

Setup cron job for daily backups:
0 2 \* \* \* /path/to/backup_database.sh
"""

# ============================================================================

# COMPLETE SETTINGS.PY TEMPLATE (Production)

# ============================================================================

"""

# In your E_marketing/settings.py:

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(**file**).resolve().parent.parent

# === SECURITY ===

SECRET_KEY = os.getenv('SECRET_KEY') # Use environment variable!
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# === DATABASE ===

DATABASES = {
'default': {
'ENGINE': 'django.db.backends.postgresql',
'NAME': os.getenv('DB_NAME', 'on_call_driver_db'),
'USER': os.getenv('DB_USER', 'postgres'),
'PASSWORD': os.getenv('DB_PASSWORD'),
'HOST': os.getenv('DB_HOST', 'localhost'),
'PORT': os.getenv('DB_PORT', '5432'),
'CONN_MAX_AGE': 600,
'OPTIONS': {
'connect_timeout': 10,
}
}
}

# === CACHING (Redis) ===

CACHES = {
'default': {
'BACKEND': 'django_redis.cache.RedisCache',
'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
'OPTIONS': {
'CLIENT_CLASS': 'django_redis.client.DefaultClient',
}
}
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# === SECURITY HEADERS ===

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ... rest of settings ...

"""

# ============================================================================

# ENVIRONMENT VARIABLES (.env file)

# ============================================================================

"""
Create file: .env

SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database

DB_ENGINE=postgresql
DB_NAME=on_call_driver_db
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=your-db-server.com
DB_PORT=5432

# Redis

REDIS_URL=redis://your-redis-server:6379/1

# WhatsApp

WHATSAPP_PHONE_NUMBER_ID=your-id
WHATSAPP_ACCESS_TOKEN=your-token
WHATSAPP_VERIFY_TOKEN=your-token

Add to .gitignore:
.env
\*.log
db.sqlite3
"""

# ============================================================================

# MIGRATION COMMANDS FOR PRODUCTION

# ============================================================================

"""

1. Test migrations in development:
   python manage.py migrate --plan
   python manage.py migrate

2. Backup database before migration:
   pg_dump on_call_driver_db > backup_before_migration.sql

3. Run migrations:
   python manage.py migrate --no-input

4. Collect static files:
   python manage.py collectstatic --noinput

5. Create cache table (if using database cache):
   python manage.py createcachetable
   """

# ============================================================================

# PRODUCTION DEPLOYMENT CHECKLIST

# ============================================================================

"""
Before going live:

SECURITY:
☐ Set DEBUG = False
☐ Update SECRET_KEY
☐ Set ALLOWED_HOSTS
☐ Enable HTTPS/SSL
☐ Set SECURE_SSL_REDIRECT = True
☐ Enable secure cookies
☐ Set up CSRF protection
☐ Add security headers

DATABASE:
☐ Switch to PostgreSQL or MySQL
☐ Set up database backups
☐ Configure connection pooling
☐ Add database indexes
☐ Set up replica for read scaling (optional)

CACHING:
☐ Set up Redis
☐ Configure cache timeout values
☐ Use cache for sessions
☐ Cache expensive queries

MONITORING:
☐ Set up error logging
☐ Monitor slow queries
☐ Set up database alerts
☐ Monitor memory usage

PERFORMANCE:
☐ Enable gzip compression
☐ Configure CDN for static files
☐ Set up load balancing (if needed)
☐ Enable query optimization

BACKUPS:
☐ Set up automated daily backups
☐ Test backup restoration
☐ Store backups off-site
"""
