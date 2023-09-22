"""
APIs for getting grade info
"""

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import staff as staff_api


class GradesAPI:
    def __init__(self, block):
        self._block = block

    def _get_submission_uuid(self):
        return self._block.submission_uuid

    @property
    def self_score(self):
        """
        Get self score.

        Returns:
        {
            "points_earned": (Int) awarded points
            "points_possible": (Int) max possible points
        }
        """
        submission_uuid = self._get_submission_uuid()
        assessment = self_api.get_assessment(submission_uuid)

        if assessment is not None:
            return {
                "points_earned": assessment["points_earned"],
                "points_possible": assessment["points_possible"],
            }
        return None

    @property
    def peer_score(self):
        """
        Refresh workflows and get peer score.

        Returns:
        {
            "points_earned": (Int) calculated peer score
            "points_possible": (Int) max possible points
        }
        """
        submission_uuid = self._get_submission_uuid()
        peer_requirements = self._block.workflow_requirements()["peer"]
        course_settings = self._block.get_course_workflow_settings()

        peer_score = peer_api.get_score(
            submission_uuid, peer_requirements, course_settings
        )

        if peer_score is not None:
            return {
                "points_earned": peer_score["points_earned"],
                "points_possible": peer_score["points_possible"],
            }
        return None

    @property
    def staff_score(self):
        """
        Get staff score.

        Returns:
        {
            "points_earned": (Int) awarded points
            "points_possible": (Int) max possible points
        }
        """
        submission_uuid = self._get_submission_uuid()
        assessment = staff_api.get_latest_staff_assessment(submission_uuid)

        if assessment is not None:
            return {
                "points_earned": assessment["points_earned"],
                "points_possible": assessment["points_possible"],
            }
        return None
