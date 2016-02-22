Installation
============

Like many Python packages, you can use several methods to install AutoPlanner.
AutoPlanner designed to run with python3.5.x+.
The following packages are also required:

  * setuptools >= 3.0
  * djangofloor >= 0.18.0


Of course you can install it from the source, but the preferred way is to install it as a standard Python package, via pip.


Installing or Upgrading
-----------------------

Here is a simple tutorial to install AutoPlanner on a basic Debian/Linux installation.
You should easily adapt it on a different Linux or Unix flavor.


Database
--------

PostgreSQL is often a good choice for Django sites:

.. code-block:: bash

   sudo apt-get install postgresql
   echo "CREATE USER autoplanner" | sudo -u postgres psql -d postgres
   echo "ALTER USER autoplanner WITH ENCRYPTED PASSWORD '5trongp4ssw0rd'" | sudo -u postgres psql -d postgres
   echo "ALTER ROLE autoplanner CREATEDB" | sudo -u postgres psql -d postgres
   echo "CREATE DATABASE autoplanner OWNER autoplanner" | sudo -u postgres psql -d postgres


AutoPlanner also requires Redis:

.. code-block:: bash

    sudo apt-get install redis-server





Apache
------

I only present the installation with Apache, but an installation behind nginx should be similar.
You cannot use different server names for browsing your mirror. If you use `autoplanner.example.org`
in the configuration, you cannot use its IP address to access the website.

.. code-block:: bash

    SERVICE_NAME=autoplanner.example.org
    sudo apt-get install apache2 libapache2-mod-xsendfile
    sudo a2enmod headers proxy proxy_http
    sudo a2dissite 000-default.conf
    # sudo a2dissite 000-default on Debian7
    cat << EOF | sudo tee /etc/apache2/sites-available/autoplanner.conf
    <VirtualHost *:80>
        ServerName $SERVICE_NAME
        Alias /static/ /var/autoplanner/static/
        ProxyPass /static/ !
        <Location /static/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
        Alias /media/ /var/autoplanner/data/media/
        ProxyPass /media/ !
        <Location /media/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
        ProxyPass / http://127.0.0.1:9000/
        ProxyPassReverse / http://127.0.0.1:9000/
        DocumentRoot /var/autoplanner/static
        ServerSignature off
        XSendFile on
        XSendFilePath /var/autoplanner/data/media
        # in older versions of XSendFile (<= 0.9), use XSendFileAllowAbove On
    </VirtualHost>
    EOF
    sudo mkdir /var/autoplanner
    sudo chown -R www-data:www-data /var/autoplanner
    sudo a2ensite autoplanner.conf
    sudo apachectl -t
    sudo apachectl restart


If you want to use SSL:

.. code-block:: bash

    sudo apt-get install apache2 libapache2-mod-xsendfile
    PEM=/etc/apache2/`hostname -f`.pem
    # ok, I assume that you already have your certificate
    sudo a2enmod headers proxy proxy_http ssl
    openssl x509 -text -noout < $PEM
    sudo chown www-data $PEM
    sudo chmod 0400 $PEM

    sudo apt-get install libapache2-mod-auth-kerb
    KEYTAB=/etc/apache2/http.`hostname -f`.keytab
    # ok, I assume that you already have your keytab
    sudo a2enmod auth_kerb
    cat << EOF | sudo ktutil
    rkt $KEYTAB
    list
    quit
    EOF
    sudo chown www-data $KEYTAB
    sudo chmod 0400 $KEYTAB

    SERVICE_NAME=autoplanner.example.org
    cat << EOF | sudo tee /etc/apache2/sites-available/autoplanner.conf
    <VirtualHost *:80>
        ServerName $SERVICE_NAME
        RedirectPermanent / https://$SERVICE_NAME/
    </VirtualHost>
    <VirtualHost *:443>
        ServerName $SERVICE_NAME
        SSLCertificateFile $PEM
        SSLEngine on
        Alias /static/ /var/autoplanner/static/
        ProxyPass /static/ !
        <Location /static/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
        Alias /media/ /var/autoplanner/data/media/
        ProxyPass /media/ !
        <Location /media/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
        ProxyPass / http://127.0.0.1:9000/
        ProxyPassReverse / http://127.0.0.1:9000/
        DocumentRoot /var/autoplanner/static
        ServerSignature off
        RequestHeader set X_FORWARDED_PROTO https
        <Location />
            AuthType Kerberos
            AuthName "AutoPlanner"
            KrbAuthRealms EXAMPLE.ORG example.org
            Krb5Keytab $KEYTAB
            KrbLocalUserMapping On
            KrbServiceName HTTP
            KrbMethodK5Passwd Off
            KrbMethodNegotiate On
            KrbSaveCredentials On
            Require valid-user
            RequestHeader set REMOTE_USER %{REMOTE_USER}s
        </Location>
        XSendFile on
        XSendFilePath /var/autoplanner/data/media
        # in older versions of XSendFile (<= 0.9), use XSendFileAllowAbove On
    </VirtualHost>
    EOF
    sudo mkdir /var/autoplanner
    sudo chown -R www-data:www-data /var/autoplanner
    sudo a2ensite autoplanner.conf
    sudo apachectl -t
    sudo apachectl restart




Application
-----------

Now, it's time to install AutoPlanner:

.. code-block:: bash

    sudo mkdir -p /var/autoplanner
    sudo adduser --disabled-password autoplanner
    sudo chown autoplanner:www-data /var/autoplanner
    sudo apt-get install virtualenvwrapper python3.5 python3.5-dev build-essential postgresql-client libpq-dev
    # application
    sudo -u autoplanner -i
    mkvirtualenv autoplanner -p `which python3.5`
    workon autoplanner
    pip install setuptools --upgrade
    pip install pip --upgrade
    pip install autoplanner psycopg2 gevent
    mkdir -p $VIRTUAL_ENV/etc/autoplanner
    cat << EOF > $VIRTUAL_ENV/etc/autoplanner/settings.ini
    [celery]
    redis_db = 13
    redis_host = localhost
    redis_port = 6379
    [database]
    engine = django.db.backends.postgresql_psycopg2
    host = localhost
    name = autoplanner
    password = 5trongp4ssw0rd
    port = 5432
    user = autoplanner
    [global]
    admin_email = admin@autoplanner.example.org
    bind_address = 127.0.0.1:9000
    data_path = /var/autoplanner
    debug = True
    default_group = Users
    extra_apps = 
    language_code = fr-fr
    protocol = http
    remote_user_header = HTTP_REMOTE_USER
    secret_key = 8FOOc2ETUHpRYqYvcZ6cvmXD2sz1W88JQjUQFpvHH0KeWRioyU
    server_name = autoplanner.example.org
    time_zone = Europe/Paris
    [sentry]
    dsn_url = 
    EOF
    chmod 0400 $VIRTUAL_ENV/etc/autoplanner/settings.ini
    # required since there are password in this file
    autoplanner-manage migrate
    autoplanner-manage collectstatic --noinput
    autoplanner-manage createsuperuser



supervisor
----------

Supervisor is required to automatically launch autoplanner:

.. code-block:: bash


    sudo apt-get install supervisor
    cat << EOF | sudo tee /etc/supervisor/conf.d/autoplanner.conf
    [program:autoplanner_gunicorn]
    command = /home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-gunicorn
    user = autoplanner
    [program:autoplanner_celery]
    command = /home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-celery worker
    user = autoplanner
    EOF
    sudo service supervisor stop
    sudo service supervisor start

Now, Supervisor should start autoplanner after a reboot.


systemd
-------

You can also use systemd to launch autoplanner:

.. code-block:: bash

    cat << EOF | sudo tee /etc/systemd/system/autoplanner-gunicorn.service
    [Unit]
    Description=AutoPlanner Gunicorn process
    After=network.target
    [Service]
    User=autoplanner
    Group=autoplanner
    WorkingDirectory=/var/autoplanner/
    ExecStart=/home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-gunicorn
    ExecReload=/bin/kill -s HUP $MAINPID
    ExecStop=/bin/kill -s TERM $MAINPID
    [Install]
    WantedBy=multi-user.target
    EOF
    systemctl enable autoplanner-gunicorn.service
    sudo service autoplanner-gunicorn start
    cat << EOF | sudo tee /etc/systemd/system/autoplanner-celery.service
    [Unit]
    Description=AutoPlanner Celery process
    After=network.target
    [Service]
    User=autoplanner
    Group=autoplanner
    WorkingDirectory=/var/autoplanner/
    ExecStart=/home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-celery worker
    ExecReload=/bin/kill -s HUP $MAINPID
    ExecStop=/bin/kill -s TERM $MAINPID
    [Install]
    WantedBy=multi-user.target
    EOF
    sudo systemctl enable autoplanner-celery.service
    sudo service autoplanner-celery start



