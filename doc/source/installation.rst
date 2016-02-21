Installing / Upgrading
======================

Here is a simple tutorial to install autoplanner on a basic Debian/Linux installation.
You should easily adapt it on a different Linux or Unix flavor.

Let's start by defining some variables:

.. code-block:: bash

    SERVICE_NAME=autoplanner.example.com

Database
--------

PostgreSQL is often a good choice for Django sites:

.. code-block:: bash

   sudo apt-get install postgresql
   echo "CREATE USER autoplanner" | sudo -u postgres psql -d postgres
   echo "ALTER USER autoplanner WITH ENCRYPTED PASSWORD 'autoplanner-5trongp4ssw0rd'" | sudo -u postgres psql -d postgres
   echo "ALTER ROLE autoplanner CREATEDB" | sudo -u postgres psql -d postgres
   echo "CREATE DATABASE autoplanner OWNER autoplanner" | sudo -u postgres psql -d postgres

Apache
------

I only present the installation with Apache, but an installation behind nginx should be similar.

.. code-block:: bash

    sudo apt-get install apache2 libapache2-mod-xsendfile
    sudo a2enmod headers proxy proxy_http
    sudo a2dissite 000-default.conf
    # sudo a2dissite 000-default on Debian7
    SERVICE_NAME=autoplanner.example.com
    cat << EOF | sudo tee /etc/apache2/sites-available/autoplanner.conf
    <VirtualHost *:80>
        ServerName $SERVICE_NAME
        Alias /static/ /var/autoplanner/static/
        Alias /media/ /var/autoplanner/media/
        ProxyPass /static/ !
        ProxyPass /media/ !
        ProxyPass / http://localhost:8001/
        ProxyPassReverse / http://localhost:8001/
        DocumentRoot /var/autoplanner/
        ServerSignature off
        <Location /static/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
    </VirtualHost>
    EOF
    sudo mkdir /var/autoplanner/
    sudo chown -R www-data:www-data /var/autoplanner/
    sudo a2ensite autoplanner.conf
    sudo apachectl -t
    sudo apachectl restart

If you want Kerberos authentication and SSL:

.. code-block:: bash

    sudo apt-get install apache2 libapache2-mod-xsendfile libapache2-mod-auth-kerb
    PEM=/etc/apache2/`hostname -f`.pem
    KEYTAB=/etc/apache2/http.`hostname -f`.keytab
    # ok, I assume that you already have your certificate and your keytab
    sudo a2enmod auth_kerb headers proxy proxy_http ssl
    openssl x509 -text -noout < $PEM
    cat << EOF | sudo ktutil
    rkt $KEYTAB
    list
    quit
    EOF
    sudo chown www-data $PEM $KEYTAB
    sudo chmod 0400 $PEM $KEYTAB

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
        Alias /media/ /var/autoplanner/media/
        ProxyPass /static/ !
        ProxyPass /media/ !
        ProxyPass / http://localhost:8001/
        ProxyPassReverse / http://localhost:8001/
        DocumentRoot /var/autoplanner/
        ServerSignature off
        RequestHeader set X_FORWARDED_PROTO https
        <Location />
            Options +FollowSymLinks +Indexes
            AuthType Kerberos
            AuthName "autoplanner"
            KrbAuthRealms EXAMPLE.ORG
            Krb5Keytab $KEYTAB
            KrbLocalUserMapping On
            KrbServiceName HTTP
            KrbMethodK5Passwd Off
            KrbMethodNegotiate On
            KrbSaveCredentials On
            Require valid-user
            RequestHeader set REMOTE_USER %{REMOTE_USER}s
        </Location>
        <Location /static/>
            Order deny,allow
            Allow from all
            Satisfy any
        </Location>
    </VirtualHost>
    EOF
    sudo mkdir /var/autoplanner/
    sudo chown -R www-data:www-data /var/autoplanner/
    sudo a2ensite autoplanner.conf
    sudo apachectl -t
    sudo apachectl restart



Application
-----------

Now, it's time to install autoplanner (use Python3.2 on Debian 7):

.. code-block:: bash

    sudo mkdir -p /var/autoplanner
    sudo adduser --disabled-password autoplanner
    sudo chown autoplanner:www-data /var/autoplanner
    sudo apt-get install virtualenvwrapper python3.4 python3.4-dev build-essential postgresql-client libpq-dev
    # application
    sudo -u autoplanner -i
    SERVICE_NAME=autoplanner.example.com
    mkvirtualenv autoplanner -p `which python3.4`
    workon autoplanner
    pip install setuptools --upgrade
    pip install pip --upgrade
    pip install autoplanner psycopg2
    mkdir -p $VIRTUAL_ENV/etc/autoplanner
    cat << EOF > $VIRTUAL_ENV/etc/autoplanner/settings.ini
    [global]
    server_name = $SERVICE_NAME
    protocol = http
    ; use https if your Apache uses SSL
    bind_address = 127.0.0.1:8001
    data_path = /var/autoplanner
    admin_email = admin@$SERVICE_NAME
    time_zone = Europe/Paris
    language_code = fr-fr
    debug = false
    remote_user_header = HTTP_REMOTE_USER
    ; leave it blank if you do not use kerberos

    [database]
    engine = django.db.backends.postgresql_psycopg2
    name = autoplanner
    user = autoplanner
    password = autoplanner-5trongp4ssw0rd
    host = localhost
    port = 5432
    EOF

    autoplanner-manage migrate
    autoplanner-manage collectstatic --noinput
    autoplanner-manage createsuperuser
    EOF


supervisor
----------

Supervisor is required to automatically launch autoplanner:

.. code-block:: bash

    sudo apt-get install supervisor
    cat << EOF | sudo tee /etc/supervisor/conf.d/autoplanner.conf
    [program:autoplanner_gunicorn]
    command = /home/autoplanner/.virtualenvs/autoplanner/bin/autoplanner-gunicorn
    user = autoplanner
    EOF
    sudo /etc/init.d/supervisor restart

Now, Supervisor should start autoplanner after a reboot.

systemd
-------

You can also use systemd to launch autoplanner:

.. code-block:: bash

    cat << EOF | sudo tee /etc/systemd/system/autoplanner-gunicorn.service
    [Unit]
    Description=autoplanner Gunicorn process
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