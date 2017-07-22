# -*- coding: utf-8 -*-

import codecs
import os.path
import re

from setuptools import setup, find_packages


version = None
for line in codecs.open(os.path.join('autoplanner', '__init__.py'), 'r', encoding='utf-8'):
    matcher = re.match(r"""^__version__\s*=\s*['"](.*)['"]\s*$""", line)
    version = version or matcher and matcher.group(1)

# get README content from README.md file
with codecs.open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

entry_points = {'console_scripts': ['autoplanner-manage = djangofloor.scripts:django',
                                    'autoplanner-celery = djangofloor.scripts:celery',
                                    'autoplanner-web = djangofloor.scripts:aiohttp']}

setup(
    name='autoplanner',
    version=version,
    description='No description yet.',
    long_description=long_description,
    author='Matthieu Gallet',
    author_email='matthieu.gallet@19pouces.net',
    license='CeCILL-B',
    url='http://autoplanner.readthedocs.org/en/latest/',
    entry_points=entry_points,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='autoplanner.tests',
    install_requires=['djangofloor', 'icalendar', 'markdown', 'django_smart_selects', ],
    setup_requires=[],
    classifiers=['Development Status :: 3 - Alpha', 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: Microsoft :: Windows', 'Operating System :: POSIX :: BSD',
                 'Operating System :: POSIX :: Linux', 'Operating System :: Unix',
                 'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
                 'Programming Language :: Python :: 3.4', 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3 :: Only'],
)
