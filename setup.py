#!/usr/bin/env python

from setuptools import setup

PACKAGES = ['common_grading', 'peer_grading']

REQUIREMENTS = [
    line.strip() for line in
    open("requirements/base.txt").readlines()
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
    install_requires=REQUIREMENTS,
)
