Requirements
============

As said before, Python is required but this is not the only requirement:

  * Python (3.5, 3.6, 3.7),
  * djangofloor>=1.1.0 Python package (automatically installed with AutoPlanner),
  * icalendar Python package (automatically installed with AutoPlanner),
  * markdown Python package (automatically installed with AutoPlanner),
  * django Python package (automatically installed with AutoPlanner),
  * a Redis server for background tasks (and optionally for sessions and cache),
  * mysqlclient (Python package) libmysqlclient and libmysqlclient-dev (system packages) if you want to use MySQL,
  * psutil (Python package) to display system information on the monitoring page,
  * psycopg2 (Python package), libpq and libpq-dev (system packages) if you want to use PostgreSQL,
  * cx_Oracle (Python package) and the associated system packages if you want to use Oracle,
  * django_redis (Python package) is you want to cache pages in Redis,
  * django-allauth (Python package) for OAuth2 authentication,
  * django-radius (Python package) for Radius authentication,
  * django-auth-ldap (Python package) and libldap-dev (system package) for LDAP authentication,
  * django_pam (Python package) for PAM authentication.

