# -*- coding: utf-8 -*-
__author__ = 'Matthieu Gallet'

########################################################################################################################
# sessions
########################################################################################################################
SESSION_REDIS_PREFIX = 'session'
SESSION_REDIS_HOST = '{REDIS_HOST}'
SESSION_REDIS_PORT = '{REDIS_PORT}'
SESSION_REDIS_DB = 10

########################################################################################################################
# django-redis-websocket
########################################################################################################################

########################################################################################################################
# celery
########################################################################################################################

FLOOR_INSTALLED_APPS = ['autoplanner', ]
FLOOR_INDEX = 'autoplanner.views.index'
FLOOR_URL_CONF = 'autoplanner.root_urls.urls'
FLOOR_PROJECT_NAME = 'AutoPlanner'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8FOOc2ETUHpRYqYvcZ6cvmXD2sz1W88JQjUQFpvHH0KeWRioyU'
LP_SOLVE_PATH = 'lp_solve'
if __name__ == '__main__':
    import doctest
    doctest.testmod()
