"""
Public interface for staff grading of team assignments, used by students/course staff.
"""
from __future__ import absolute_import

import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def submitter_is_finished(team_submission_uuid, team_requirements):  # pylint: disable=unused-argument
    """
    Determine if the submitter has finished their requirements for staff
    assessment. Always returns True.

    Args:
        team_submission_uuid (str): Not used.
        team_requirements (dict): Not used.

    Returns:
        True

    """
    return True
