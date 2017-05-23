# -*- coding: utf-8 -*-

__author__ = 'Matthieu Gallet'

########################################################################################################################
# celery
########################################################################################################################

DF_INSTALLED_APPS = ['autoplanner', 'smart_selects']
DF_JS = ['admin/js/core.js', 'admin/js/calendar.js', 'admin/js/admin/DateTimeShortcuts.js',
         'autoplanner/js/autoplanner.js']
DF_CSS = ['autoplanner/css/autoplanner.css']
DF_INDEX_VIEW = 'autoplanner.views.index'
DF_PROJECT_NAME = 'AutoPlanner'
DF_SITE_SEARCH_VIEW = None
# Make this unique, and don't share it with anybody.
LP_SOLVE_PATH = 'lp_solve'
REFRESH_DURATION = '1H'
