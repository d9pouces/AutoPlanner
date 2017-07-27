AutoPlanner
===========

Explications :

  * pas de  


  * génération d'un .ics global et d'ICS pour chaque personne
  * afficher un calendrier
  * statistiques par personne et par catégorie (# événements et temps total)
  * respect des contraintes (#temps min, #temps max)
  * limiter les agents possibles à ceux de l'organisation 
  * limiter les catégories possibles à celles de l'organisation
  * créer un token par agent
  * faire une action pour fixer les agents sur les tâches
  * faire un bouton pour fixer les agents des tâches passées
  * ajouter le bonus pour les tâches 
  
amqp==1.4.9
anyjson==0.3.3
appnope==0.1.0
-e git+https://github.com/d9pouces/AutoPlanner.git@d918eb6c307714815649abb1bed99bce951a901b#egg=autoplanner
billiard==3.3.0.22
celery==3.1.20
Django==1.9.2
django-allauth==0.24.1
django-bootstrap3==6.2.2
django-debug-toolbar==1.4
django-pipeline==1.6.5
django-redis==4.3.0
django-redis-cache==1.6.5
-e git+https://github.com/d9pouces/django-floor.git@fe9557dff5dc28dd948f05637117420d1a903d80#egg=djangofloor
funcsigs==0.4
gunicorn==19.4.5
icalendar==3.9.2
kombu==3.0.33
Markdown==2.6.5
MarkupSafe==0.23
oauthlib==1.0.3
path.py==8.1.2
pexpect==4.0.1
pickleshare==0.6
ptyprocess==0.5.1
python-dateutil==2.4.2
python3-openid==3.0.9
pytz==2015.7
redis==2.10.5
requests==2.9.1
