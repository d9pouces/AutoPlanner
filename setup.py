import os.path
import re

from setuptools import setup, find_packages
import os.path
import re

from setuptools import setup, find_packages

version = None
for line in open(os.path.join('autoplanner', '__init__.py'), 'r', encoding='utf-8'):
    matcher = re.match(r"""^__version__\s*=\s*['"](.*)['"]\s*$""", line)
    version = version or matcher and matcher.group(1)

# get README content from README.md file
with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as fd:
    long_description = fd.read()

setup(
    name='autoplanner',
    version=version,
    description='No description yet.',
    long_description=long_description,
    author='Matthieu Gallet',
    author_email='matthieu.gallet@19pouces.net',
    license='CeCILL-B',
    url='http://autoplanner.readthedocs.org/en/latest/',
    entry_points={'console_scripts': ['autoplanner-ctl = djangofloor.scripts:control']},
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='autoplanner.tests',
    install_requires=['djangofloor>=1.1.0', 'icalendar', 'markdown', 'django', ],
    setup_requires=[],
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Framework :: Django :: 1.11',
                 'Framework :: Django :: 2.0',
                 'Natural Language :: English',
                 'Natural Language :: French',
                 'Operating System :: MacOS :: MacOS X',
                 'Operating System :: POSIX :: BSD',
                 'Operating System :: POSIX :: Linux',
                 'Operating System :: Unix',
                 'License :: OSI Approved :: CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3 :: Only'
                 ],
)
