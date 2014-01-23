#!/usr/bin/env python

from setuptools import setup

PACKAGES = ['submissions', 'openassessment.peer']


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement;
    that is, it is not blank, a comment, or editable.
    """
    # Remove whitespace at the start/end of the line
    line = line.strip()

    # Skip blank lines, comments, and editable installs
    return not (line == ''  or line.startswith('#') or line.startswith('-e'))


REQUIREMENTS = [
    line.strip() for line in
    open("requirements/base.txt").readlines()
    if is_requirement(line)
]


setup(
    name='edx-tim',
    version='0.0.1',
    author='edX',
    url='http://github.com/edx/edx-tim',
    description='edx-tim',
    license='AGPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=PACKAGES,
    package_dir={'': 'apps'},
    install_requires=REQUIREMENTS,
)
