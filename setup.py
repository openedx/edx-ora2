#!/usr/bin/env python
from setuptools import setup

PACKAGES = [
    'openassessment',
    'openassessment.assessment',
    'openassessment.fileupload',
    'openassessment.workflow',
    'openassessment.management',
    'openassessment.xblock'
]

def is_requirement(line):
    """
    Return True if the requirement line is a package requirement;
    that is, it is not blank, a comment, or editable.
    """
    # Remove whitespace at the start/end of the line
    line = line.strip()

    # Skip blank lines, comments, and editable installs
    return not (
        line == '' or
        line.startswith('-r') or
        line.startswith('#') or
        line.startswith('-e') or
        line.startswith('git+')
    )

def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.
    Returns a list of requirement strings.
    """
    requirements = set()
    for path in requirements_paths:
        requirements.update(
            line.strip() for line in open(path).readlines()
            if is_requirement(line)
        )
    return list(requirements)

setup(
    name='ora2',
    version='0.2.4',
    author='edX',
    url='http://github.com/edx/edx-ora2',
    description='edx-ora2',
    license='AGPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=PACKAGES,
    install_requires=load_requirements('requirements/base.txt', 'requirements/wheels.txt'),
    tests_require=load_requirements('requirements/test.txt'),
    entry_points={
        'xblock.v1': [
            'openassessment = openassessment.xblock.openassessmentblock:OpenAssessmentBlock',
        ]
    },
)
