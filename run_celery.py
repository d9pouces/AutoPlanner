#!/usr/bin/env python
# -*- coding: utf-8 -*-
from djangofloor.scripts import celery
import os
os.environ['DJANGOFLOOR_PROJECT_NAME'] = 'autoplanner'
celery()