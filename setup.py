#!/usr/bin/env python

import os
import re
import os.path
from io import open as open_as_of_py3
import os.path

from setuptools import find_packages, setup

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


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


VERSION = get_version("openassessment", "__init__.py")


setup(
    name='ora2',
    version=VERSION,
    author='edX',
    author_email='oscm@edx.org',
    url='http://github.com/openedx/edx-ora2',
    description='edx-ora2',
    license='AGPL',
    long_description=README,
    long_description_content_type='text/x-rst',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django :: 3.2',
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
