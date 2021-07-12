#!/usr/bin/env python


import os.path
from io import open as open_as_of_py3

from setuptools import setup, find_packages

README = open_as_of_py3(
    os.path.join(os.path.dirname(__file__), 'README.rst')
).read()


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement;
    that is, it is not blank, a comment, a URL, or an included file.
    """
    return line and not line.startswith(('-r', '#', '-e', 'git+', '-c'))


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.
    Returns a list of requirement strings.
    """
    requirements = set()
    for path in requirements_paths:
        with open(path) as reqs:
            requirements.update(
                line.split('#')[0].strip() for line in reqs
                if is_requirement(line.strip())
            )
    return list(requirements)


setup(
    name='ora2',
    version='3.6.10',
    author='edX',
    author_email='oscm@edx.org',
    url='http://github.com/edx/edx-ora2',
    description='edx-ora2',
    license='AGPL',
    long_description=README,
    long_description_content_type='text/x-rst',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django :: 2.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    packages=find_packages(include=['openassessment*'], exclude=['*.test', '*.tests']),
    include_package_data=True,
    # Todo - this should be loading 'requirements/base.in' but Tox is having an issue with it
    install_requires=load_requirements('requirements/base.in'),
    tests_require=load_requirements('requirements/test.in'),
    entry_points={
        'xblock.v1': [
            'openassessment = openassessment.xblock.openassessmentblock:OpenAssessmentBlock',
        ]
    },
)
