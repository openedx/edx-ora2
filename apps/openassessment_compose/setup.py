"""Setup for openassessment_compose XBlock."""

import os
from setuptools import setup


def package_data(pkg, root):
    """Generic function to find package_data for `pkg` under `root`."""
    data = []
    for dirname, _, files in os.walk(os.path.join(pkg, root)):
        for fname in files:
            data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='openassessment_compose-xblock',
    version='0.1',
    description='openassessment Composition XBlock',   
    packages=[
        'openassessment_compose',
    ],
    install_requires=[
        'XBlock',
        'Mako',    # XXX: convert to django template, eliminate dependency
    ],
    entry_points={
        'xblock.v1': [
            'openassessment_compose = openassessment_compose:openassessmentComposeXBlock',
        ]
    },
    package_data=package_data("openassessment_compose", "static"),
)
