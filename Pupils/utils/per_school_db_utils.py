import logging
from django.conf import settings
from django.core.management import call_command
from django.db import connections
# from ..models import MasterSchool   # make sure this path is correct

logger = logging.getLogger(__name__)


# Add a school DB dynamically from MasterSchool info
import logging, os
from django.conf import settings
from django.db import connections
import dj_database_url

logger = logging.getLogger(__name__)

BASE_DB_CONFIG = {
    'ENGINE': 'django.db.backends.mysql',
    'HOST': 'localhost', #containers-us-west-42.railway.app',
    'PORT': '3306',
    'NAME': '',  # will be overwritten
    'USER': '',  # will be overwritten
    'PASSWORD': '',  # will be overwritten
    'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'TIME_ZONE': settings.TIME_ZONE,
    'CONN_HEALTH_CHECKS': [],
    'CONN_MAX_AGE': settings.DATABASES['default'].get('CONN_MAX_AGE', 0),
}



def add_school_database(db_name, db_user, db_password,
                        host='localhost', port='3306', alias = None, engine=None):
    """
    Dynamically add a new school database connection.
    - Locally: uses MySQL with provided args.
    - On Render: parses DATABASE_URL (Postgres).
    """
    alias = alias or db_name

    if os.getenv("DATABASE_URL"):  
        # Render / production → Postgres
        db_entry = dj_database_url.parse(os.getenv("DATABASE_URL"))
        db_entry.setdefault('OPTIONS', {})
        db_entry.setdefault('TIME_ZONE', settings.TIME_ZONE)
        db_entry.setdefault('CONN_MAX_AGE', settings.DATABASES['default'].get('CONN_MAX_AGE', 0))
        db_entry.setdefault("AUTOCOMMIT", True)
        db_entry.setdefault("ATOMIC_REQUESTS", False)
    else:
        # Local → MySQL
        engine = engine or 'django.db.backends.mysql'
        db_entry = {
            **BASE_DB_CONFIG,
            'ENGINE': engine,
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': host,
            'PORT': port,
            'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
        }

    # Add to settings
    settings.DATABASES[alias] = db_entry

    # Reset connection if already exists
    try:
        del connections[alias]
    except (KeyError, AttributeError):
        pass

    logger.info("Database [%s] registered in settings.DATABASES", alias)
    return alias



def migrate_school_database(alias):
    """Run migrations for the given school database"""
    call_command('migrate', database=alias, interactive=False, verbosity=1)


def set_school_db_alias_in_session(request, alias):
    request.session['school_db_alias'] = alias


def get_school_db_alias_from_session(request, default='default'):
    return request.session.get('school_db_alias', default)


# def ensure_school_database(request):
#     """
#     Ensure the current session's school database alias is registered.
#     If not, rebuild it from MasterSchool.
#     """
#     alias = get_school_db_alias_from_session(request)
#     if not alias or alias == 'default':
#         return None

#     if alias not in settings.DATABASES:
#         # Try to recover school info from MasterSchool
#         school_name = alias.replace("school_", "").replace("_", " ")
#         try:
#             school = MasterSchool.objects.get(school_name__iexact=school_name)
#             real_password = school.get_db_password()
#             add_school_database(
#                 db_name=f"school_{school.school_name.lower().replace(' ', '_')}",
#                 db_user=school.db_user,
#                 db_password=real_password,
#                 alias=alias
#             )
#             logger.info("Rebuilt DB alias for %s from MasterSchool", alias)
#         except MasterSchool.DoesNotExist:
#             logger.error("Could not rebuild DB alias %s from MasterSchool", alias)
#             return None

#     return alias
