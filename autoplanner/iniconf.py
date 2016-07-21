# -*- coding: utf-8 -*-
from djangofloor.iniconf import INI_MAPPING as DEFAULTS, OptionParser

__author__ = 'Matthieu Gallet'

INI_MAPPING = DEFAULTS + [OptionParser('REDIS_HOST', 'celery.redis_host'),
                          OptionParser('REDIS_PORT', 'celery.redis_port'),
                          OptionParser('BROKER_DB', 'celery.redis_db', int),
                          OptionParser('REFRESH_DURATION', 'global.refresh_duration')]