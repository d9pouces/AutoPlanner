
Complete configuration
======================


Configuration options
---------------------

You can look current settings with the following command:

.. code-block:: bash

    autoplanner-manage config

Here is the complete list of settings:

.. code-block:: ini

  [celery]
  redis_db = 13
  # database name of your Celery instance
  redis_host = localhost
  # hostname of your Redis database for Redis-based services (cache, Celery, websockets, sessions)
  redis_port = 6379
  # port of your Redis database
  [database]
  engine = django.db.backends.postgresql
  # SQL database engine, can be 'django.db.backends.[postgresql|mysql|sqlite3|oracle]'.
  host = localhost
  # Empty for localhost through domain sockets or "127.0.0.1" for localhost + TCP
  name = autoplanner
  # Name of your database, or path to database file if using sqlite3.
  password = 5trongp4ssw0rd
  # Database password (not used with sqlite3)
  port = 5432
  # Database port, leave it empty for default (not used with sqlite3)
  user = autoplanner
  # Database user (not used with sqlite3)
  [global]
  admin_email = admin@autoplanner.example.org
  # error logs are sent to this e-mail address
  bind_address = 127.0.0.1:9000
  # The socket (IP address:port) to bind to.
  data_path = /var/autoplanner
  # Base path for all data
  debug = True
  # A boolean that turns on/off debug mode.
  default_group = Users
  # Name of the default group for newly-created users.
  extra_apps = 
  # List of extra installed Django apps (separated by commas).
  language_code = fr-fr
  # A string representing the language code for this installation.
  protocol = http
  # Protocol (or scheme) used by your webserver (apache/nginx/…, can be http or https)
  remote_user_header = HTTP_REMOTE_USER
  # HTTP header corresponding to the username when using HTTP authentication.Should be "HTTP_REMOTE_USER". Leave it empty to disable HTTP authentication.
  secret_key = 8FOOc2ETUHpRYqYvcZ6cvmXD2sz1W88JQjUQFpvHH0KeWRioyU
  # A secret key for a particular Django installation. This is used to provide cryptographic signing, and should be set to a unique, unpredictable value.
  server_name = autoplanner.example.org
  # the name of your webserver (should be a DNS name, but can be an IP address)
  time_zone = Europe/Paris
  # A string representing the time zone for this installation, or None. 
  [sentry]
  dsn_url = 
  # Sentry URL to send data to. https://docs.getsentry.com/



If you need more complex settings, you can override default values (given in `djangofloor.defaults` and
`autoplanner.defaults`) by creating a file named `/home/autoplanner/.virtualenvs/autoplanner/etc/autoplanner/settings.py`.



Debugging
---------

If something does not work as expected, you can look at logs (in /var/log/supervisor if you use supervisor)
or try to run the server interactively:

.. code-block:: bash

  sudo service supervisor stop
  sudo -u autoplanner -i
  workon autoplanner
  autoplanner-manage config
  autoplanner-manage runserver
  autoplanner-gunicorn
  autoplanner-celery worker




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
  sudo -u autoplanner -i
  cat << EOF > /home/autoplanner/.virtualenvs/autoplanner/etc/autoplanner/backup_db.conf
  /var/backups/autoplanner/backup_db.sql.gz {
    daily
    rotate 20
    nocompress
    missingok
    create 640 autoplanner autoplanner
    postrotate
    myproject-manage dumpdb | gzip > /var/backups/autoplanner/backup_db.sql.gz
    endscript
  }
  EOF
  touch /var/backups/autoplanner/backup_db.sql.gz
  crontab -e
  MAILTO=admin@autoplanner.example.org
  0 1 * * * /home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-manage clearsessions
  0 2 * * * logrotate -f /home/autoplanner/.virtualenvs/autoplanner/etc/autoplanner/backup_db.conf


Backup of the user-created files can be done with rsync, with a full backup each month:
If you have a lot of files to backup, beware of the available disk place!

.. code-block:: bash

  sudo mkdir -p /var/backups/autoplanner/media
  sudo chown -r autoplanner: /var/backups/autoplanner
  cat << EOF > /home/autoplanner/.virtualenvs/autoplanner/etc/autoplanner/backup_media.conf
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
  MAILTO=admin@autoplanner.example.org
  0 3 * * * rsync -arltDE /var/autoplanner/data/media/ /var/backups/autoplanner/media/
  0 5 0 * * logrotate -f /home/autoplanner/.virtualenvs/autoplanner/etc/autoplanner/backup_media.conf

Restoring a backup
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

  cat /var/backups/autoplanner/backup_db.sql.gz | gunzip | /home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-manage dbshell
  tar -C /var/autoplanner/data/media/ -xf /var/backups/autoplanner/backup_media.tar.gz





Monitoring
----------


Nagios or Shinken
~~~~~~~~~~~~~~~~~

You can use Nagios checks to monitor several points:

  * connection to the application server (gunicorn or uwsgi):
  * connection to the database servers (PostgreSQL and Redis),
  * connection to the reverse-proxy server (apache or nginx),
  * the validity of the SSL certificate (can be combined with the previous check),
  * creation date of the last backup (database and files),
  * living processes for gunicorn, celery, redis, postgresql, apache,
  * standard checks for RAM, disk, swap…

Here is a sample NRPE configuration file:

.. code-block:: bash

  cat << EOF | sudo tee /etc/nagios/nrpe.d/autoplanner.cfg
  command[autoplanner_wsgi]=/usr/lib/nagios/plugins/check_http -H 127.0.0.1 -p 9000
  command[autoplanner_redis]=/usr/lib/nagios/plugins/check_tcp -H localhost -p 6379
  command[autoplanner_database]=/usr/lib/nagios/plugins/check_tcp -H localhost -p 5432
  command[autoplanner_reverse_proxy]=/usr/lib/nagios/plugins/check_http -H autoplanner.example.org -p 80 -e 401
  command[autoplanner_backup_db]=/usr/lib/nagios/plugins/check_file_age -w 172800 -c 432000 /var/backups/autoplanner/backup_db.sql.gz
  command[autoplanner_backup_media]=/usr/lib/nagios/plugins/check_file_age -w 3024000 -c 6048000 /var/backups/autoplanner/backup_media.sql.gz
  command[autoplanner_gunicorn]=/usr/lib/nagios/plugins/check_procs -C python -a '/home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-gunicorn'
  command[autoplanner_celery]=/usr/lib/nagios/plugins/check_procs -C python -a '/home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-celery worker'
  EOF

Sentry
~~~~~~

For using Sentry to log errors, you must add `raven.contrib.django.raven_compat` to the installed apps.

.. code-block:: ini

  [global]
  extra_apps = raven.contrib.django.raven_compat
  [sentry]
  dsn_url = https://[key]:[secret]@app.getsentry.com/[project]

Of course, the Sentry client (Raven) must be separately installed, before testing the installation:

.. code-block:: bash

  sudo -u autoplanner -i
  autoplanner-manage raven test





LDAP groups
-----------

There are two possibilities to use LDAP groups, with their own pros and cons:

  * on each request, use an extra LDAP connection to retrieve groups instead of looking in the SQL database,
  * regularly synchronize groups between the LDAP server and the SQL servers.

The second approach can be used without any modification in your code and remove a point of failure
in the global architecture (if you allow some delay during the synchronization process).
A tool exists for such synchronization: `MultiSync <https://github.com/d9pouces/Multisync>`_.
