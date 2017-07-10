#!/usr/bin/env python3
from djangofloor.scripts import celery
import os
os.environ['DJANGOFLOOR_PROJECT_NAME'] = 'autoplanner'
celery()
