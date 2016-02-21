# -*- coding: utf-8 -*-
from djangofloor.utils import ExpandIterable

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

DEBUG = False
USE_CELERY = True


PIPELINE_CSS = {
    'default': {
        'source_filenames': ['bootstrap3/css/bootstrap.min.css', 'css/font-awesome.min.css',
                             'css/bootstrap-select.min.css', 'css/djangofloor.css',
                             ExpandIterable('FLOOR_EXTRA_CSS'), ],
        'output_filename': 'css/default.css',
        'extra_context': {
            'media': 'all',
        },
    },
    'metango': {
        'source_filenames': [
            'css/metro.min.css',
            'css/metro-icons.min.css',
            'css/metro-responsive.min.css',
            'css/metro-schemes.min.css',
            'css/metro-rtl.min.css',
            'css/jquery.dataTables.min.css',
            'css/select2.min.css',
        ],
        'output_filename': 'css/metango.css',
        'extra_context': {
            'media': 'all',
        },
    },
}
PIPELINE_JS = {
    'default': {
        'source_filenames': ['js/jquery.min.js', 'bootstrap3/js/bootstrap.min.js',
                             'js/bootstrap-notify.min.js', 'js/djangofloor.js', 'js/bootstrap-select.min.js',
                             'js/ws4redis.js', ExpandIterable('FLOOR_EXTRA_JS'), ],
        'output_filename': 'js/default.js',
    },
    'metango': {
        'source_filenames': [
            'js/jquery.min.js',
            'js/metro.min.js',
            'js/jquery.dataTables.min.js',
            'js/select2.full.min.js',
            'js/djangofloor.js',
            'js/ws4redis.js',
        ],
        'output_filename': 'js/metango.js',
    },
    'ie9': {
        'source_filenames': ['js/html5shiv.js', 'js/respond.min.js', ],
        'output_filename': 'js/ie9.js',
    }
}
