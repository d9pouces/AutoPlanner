#!/usr/bin/env python3
from djangofloor.scripts import control, set_env

__author__ = 'Matthieu Gallet'

set_env(command_name='autoplanner-django')
if __name__ == "__main__":
    control()
