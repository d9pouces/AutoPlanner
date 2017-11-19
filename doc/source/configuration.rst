
Complete configuration
======================


Configuration options
---------------------

You can look current settings with the following command:

.. code-block:: bash

    autoplanner-manage config ini -v 2

You can also display the actual list of Python settings

.. code-block:: bash

    autoplanner-manage config python -v 2


Here is the complete list of settings:

.. code-block:: ini

  [auth]
  allow_basic_auth = True 
  	# Set to "true" if you want to allow HTTP basic auth, using the Django database.
  ldap_bind_dn =  
  	# Bind dn for LDAP authentication
  ldap_bind_password =  
  	# Bind password for LDAP authentication
  ldap_direct_bind =  
  	# Set it for a direct LDAP bind, like "uid=%(user)s,ou=users,dc=example,dc=com"
  ldap_filter = (uid=%(user)s) 
  	# Filter for LDAP authentication, like "(uid=%(user)s)".
  ldap_search_base = ou=users,dc=example,dc=com 
  	# Search base for LDAP authentication, like "ou=users,dc=example,dc=com".
  ldap_server_url =  
  	# URL of your LDAP server, like "ldap://ldap.example.com". Python packages "pyldap" and "django-auth-ldap" must be installed.
  ldap_start_tls = False
  remote_user_groups = Users 
  	# Comma-separated list of groups, for new users that automatically created when authenticated by a HTTP header.
  remote_user_header =  
  	# Set it if you want to use HTTP authentication, a common value is "HTTP-REMOTE-USER".
  
  [cache]
  db = 2 
  	# Database number of the Redis Cache DB. 
  	# Python package "django-redis" is required.
  host = localhost 
  	# Redis Cache DB host
  password =  
  	# Redis Cache DB password (if required)
  port = 6379 
  	# Redis Cache DB port
  
  [celery]
  db = 4 
  	# Database number of the Redis Celery DB 
  	# Celery is used for processing background tasks and websockets.
  host = localhost 
  	# Redis Celery DB host
  password =  
  	# Redis Celery DB password (if required)
  port = 6379 
  	# Redis Celery DB port
  redis_db = [[]]
  redis_host = [[]]
  redis_port = [[]]
  
  [database]
  db = /home/usr/.virtualenvs/autoplanner35/var/autoplanner/database.sqlite3
  	# Main database name (or path of the sqlite3 database)
  engine = sqlite3 
  	# Main database engine ("mysql", "postgresql", "sqlite3", "oracle", or the dotted name of the Django backend)
  host =  
  	# Main database host
  password =  
  	# Main database password
  port =  
  	# Main database port
  user =  
  	# Main database user
  
  [email]
  from = admin@localhost 
  	# Displayed sender email
  host = localhost 
  	# SMTP server
  password =  
  	# SMTP password
  port = 25 
  	# SMTP port (often 25, 465 or 587)
  use_ssl = False 
  	# "true" if your SMTP uses SSL (often on port 465)
  use_tls = False 
  	# "true" if your SMTP uses STARTTLS (often on port 587)
  user =  
  	# SMTP user
  
  [global]
  admin_email = admin@localhost 
  	# e-mail address for receiving logged errors
  data = /home/usr/.virtualenvs/autoplanner35/var/autoplanner
  	# where all data will be stored (static/uploaded/temporary files, …). If you change it, you must run the collectstatic and migrate commands again.
  language_code = fr-fr 
  	# default to fr_FR
  listen_address = localhost:9000 
  	# address used by your web server.
  log_remote_url =  
  	# Send logs to a syslog or systemd log daemon.  
  	# Examples: syslog+tcp://localhost:514/user, syslog:///local7, syslog:///dev/log/daemon, logd:///project_name
  log_slow_queries_duration =  
  	# DB queries that take more than this threshold (in seconds) are logged.Deactivated if left empty.
  refresh_duration = 1H
  server_url = http://localhost:9000/ 
  	# Public URL of your website.  
  	# Default to "http://listen_address" but should be ifferent if you use a reverse proxy like Apache or Nginx. Example: http://www.example.org.
  time_zone = Europe/Paris 
  	# default to Europe/Paris
  
  [server]
  processes = 2 
  	# The number of Gunicorn processes for handling requests.
  threads = 2 
  	# The number of Gunicorn threads for handling requests.
  timeout = 30 
  	# Workers silent for more than this many seconds are killed and restarted.
  
  [sessions]
  db = 3 
  	# Database number of the Redis sessions DB 
  	# Python package "django-redis-sessions" is required.
  host = localhost 
  	# Redis sessions DB host
  password =  
  	# Redis sessions DB password (if required)
  port = 6379 
  	# Redis sessions DB port
  
  [websocket]
  db = 3 
  	# Database number of the Redis websocket DB
  host = localhost 
  	# Redis websocket DB host
  password =  
  	# Redis websocket DB password (if required)
  port = 6379 
  	# Redis websocket DB port
  



If you need more complex settings, you can override default values (given in `djangofloor.defaults` and
`autoplanner.defaults`) by creating a file named `/autoplanner/settings.py`.



Optional components
-------------------

Efficient page caching
~~~~~~~~~~~~~~~~~~~~~~

You just need to install `django-redis`.
Settings are automatically changed for using a local Redis server (of course, you can change it in your config file).

.. code-block:: bash

  pip install django-redis

Faster session storage
~~~~~~~~~~~~~~~~~~~~~~

You just need to install `django-redis-sessions` for storing sessions into user sessions in Redis instead of storing them in the main database.
Redis is not designed to be backuped; if you loose your Redis server, sessions are lost and all users must login again.
However, Redis is faster than your main database server and sessions take a huge place if they are not regularly cleaned.
Settings are automatically changed for using a local Redis server (of course, you can change it in your config file).

.. code-block:: bash

  pip install django-redis-sessions

Optimized media files
~~~~~~~~~~~~~~~~~~~~~

You can use `Django-Pipeline <https://django-pipeline.readthedocs.io/en/latest/configuration.html>`_ to merge all media files (CSS and JS) for a faster site.

.. code-block:: bash

  pip install django-pipeline

Optimized JavaScript files are currently deactivated due to syntax errors in generated files (not my fault ^^).



Debugging
---------

If something does not work as expected, you can look at logs (in /var/log/supervisor if you use supervisor)
or try to run the server interactively:

.. code-block:: bash

  sudo service supervisor stop
  sudo -H -u autoplanner -i
  workon autoplanner
  autoplanner-manage config
  autoplanner-manage runserver
  autoplanner-web
  autoplanner-celery worker -Q celery,fast




Backup
------

A complete AutoPlanner installation is made a different kinds of files:

    * the code of your application and its dependencies (you should not have to backup them),
    * static files (as they are provided by the code, you can lost them),
    * configuration files (you can easily recreate it, or you must backup it),
    * database content (you must backup it),
    * user-created files (you must also backup them).

Many backup strategies exist, and you must choose one that fits your needs. We can only propose general-purpose strategies.

We use logrotate to backup the database, with a new file each day.

.. code-block:: bash

  sudo mkdir -p /var/backups/autoplanner
  sudo chown -r autoplanner: /var/backups/autoplanner
  sudo -H -u autoplanner -i
  cat << EOF > /etc/autoplanner/backup_db.conf
  /var/backups/autoplanner/backup_db.sql.gz {
    daily
    rotate 20
    nocompress
    missingok
    create 640 autoplanner autoplanner
    postrotate
    moneta-manage dumpdb | gzip > /var/backups/autoplanner/backup_db.sql.gz
    endscript
  }
  EOF
  touch /var/backups/autoplanner/backup_db.sql.gz
  crontab -e
  MAILTO=admin@localhost
  0 1 * * * autoplanner-manage clearsessions
  0 2 * * * logrotate -f /etc/autoplanner/backup_db.conf


Note that clearing sessions is not required with Redis.


Backup of the user-created files can be done with rsync, with a full backup each month:
If you have a lot of files to backup, beware of the available disk place!

.. code-block:: bash

  sudo mkdir -p /var/backups/autoplanner/media
  sudo chown -r autoplanner: /var/backups/autoplanner
  cat << EOF > /etc/autoplanner/backup_media.conf
  /var/backups/autoplanner/backup_media.tar.gz {
    monthly
    rotate 6
    nocompress
    missingok
    create 640 autoplanner autoplanner
    postrotate
    tar -C /var/backups/autoplanner/media/ -czf /var/backups/autoplanner/backup_media.tar.gz .
    endscript
  }
  EOF
  touch /var/backups/autoplanner/backup_media.tar.gz
  crontab -e
  MAILTO=admin@localhost
  0 3 * * * rsync -arltDE /home/usr/.virtualenvs/autoplanner35/var/autoplanner/media/ /var/backups/autoplanner/media/
  0 5 0 * * logrotate -f /etc/autoplanner/backup_media.conf

Restoring a backup
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

  cat /var/backups/autoplanner/backup_db.sql.gz | gunzip | autoplanner-manage dbshell
  tar -C /home/usr/.virtualenvs/autoplanner35/var/autoplanner/media/ -xf /var/backups/autoplanner/backup_media.tar.gz






LDAP groups
-----------

There are two possibilities to use LDAP groups, with their own pros and cons:

  * on each request, use an extra LDAP connection to retrieve groups instead of looking in the SQL database,
  * regularly synchronize groups between the LDAP server and the SQL servers.

The second approach can be used without any modification in your code and remove a point of failure
in the global architecture (if you can afford regular synchronizations instead of instant replication).
At least one tool exists for such synchronization: `MultiSync <https://github.com/d9pouces/Multisync>`_.
