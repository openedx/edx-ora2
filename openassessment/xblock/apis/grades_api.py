"""
APIs for getting grade info
"""

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import staff as staff_api


class GradesAPI:
    def __init__(self, block):
        self._block = block
        self.workflow_data = block.workflow_data

    def _get_submission_uuid(self):
        return self._block.submission_uuid

    @property
    def score_overridden(self):
        """
        Determine if score was overridden by staff.
        Adapted from grade_mixin._get_assessment_type.

        Returns: True if score was overridden by staff, False otherwise.
        """
        workflow = self.workflow_data.workflow
        score = workflow['score']

        complete = score is not None
        grade_annotation_types = [annotation['annotation_type'] for annotation in (score or {}).get("annotations", [])]
        if complete and "staff_defined" in grade_annotation_types:
            return True

        return False

    @property
    def effective_assessment_type(self):
        """
        Determine which assessment step we will use as our "graded" step.

        This follows the order:
        1) Staff (if assessment received / overridden)
        2) Peer (if assessment step configured)
        3) Self (if assessment step configured)

        NOTE: The logic in a few places differs, but this combines the best I've found.
        """
        if self.staff_score is not None or self.score_overridden:
            return "staff"
        elif "peer-assessment" in self._block.assessment_steps:
            return "peer"
        elif "self-assessment" in self._block.assessment_steps:
            return "self"

        # To make pylint happy
        return None

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
        if submission_uuid is None:
            return None

        peer_requirements = self._block.workflow_requirements().get('peer')
        if peer_requirements is None:
            return None

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
