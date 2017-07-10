#!/usr/bin/env python3
import os
os.environ['DJANGOFLOOR_PROJECT_NAME'] = 'autoplanner'
from djangofloor.scripts import gunicorn
gunicorn()
