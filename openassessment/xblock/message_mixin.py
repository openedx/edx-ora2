"""
Message step in the OpenAssessment XBlock.
"""

from __future__ import absolute_import

import datetime as dt

import pytz

from xblock.core import XBlock


class MessageMixin:
    """
    Message Mixin introduces all handlers for displaying the banner message

    MessageMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    MessageMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.
    """

    @XBlock.handler
    def render_message(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Render the message step.

        Args:
            data: Not used.

        Keyword Arguments:
            suffix: Not used.

        Returns:
            unicode: HTML content of the message banner.
        """
        # Retrieve the status of the workflow and information about deadlines.
        workflow = self.get_workflow_info()
        deadline_info = self._get_deadline_info()

        # Finds the cannonical status of the workflow and the is_closed status of the problem
        status = workflow.get('status')
        status_details = workflow.get('status_details', {})

        problem_is_closed = deadline_info.get('general').get('is_closed')

        # Finds the deadline info of the current step (defaults to submission)
        active_step_deadline_info = deadline_info.get(status, deadline_info.get("submission"))

        # Render the instruction message based on the status of the workflow
        # and the closed status.
        if self.teams_enabled and not self.valid_access_to_team_assessment():
            path, context = self.render_message_no_team()
        elif status == "done" or status == "waiting":
            path, context = self.render_message_complete(status_details)
        elif problem_is_closed or active_step_deadline_info.get('is_closed'):
            path, context = self.render_message_closed(active_step_deadline_info)
        elif status == "self" or status == "peer" or status == "training":
            path, context = self.render_message_incomplete(status, deadline_info)
        elif status is None:
            path, context = self.render_message_open(deadline_info)
        else:
            # Default path leads to an "instruction-unavailable" block
            # Default context is empty
            path, context = 'openassessmentblock/message/oa_message_unavailable.html', {}

        context['xblock_id'] = self.get_xblock_id()
        return self.render_assessment(path, context)

    def render_message_incomplete(self, status, deadline_info):
        """
        Renders the "Incomplete" message state (User action still needed)

        Args:
            status (String): indicates the current step to be completed
            deadline_info (dict): The dictionary of boolean assessment near/closed states

        Returns:
            The path (String) and context (dict) to render the "Incomplete" message template
        """
        step_info = deadline_info.get(status, {})

        context = {
            status: True,
            "{}_approaching".format(status): step_info.get('approaching', False),
            "{}_not_released".format(status): (step_info.get("reason") == "start"),

            # Uses a static field in the XBlock to determine if the PeerAssessment Block
            # was able to pick up an assessment.
            "peer_not_available": self.no_peers,
        }

        return 'openassessmentblock/message/oa_message_incomplete.html', context

    def render_message_complete(self, status_details):
        """
        Renders the "Complete" message state (Either Waiting or Done)

        Args:
            status (String): indicates the canonical status of the workflow

        Returns:
            The path (String) and context (dict) to render the "Complete" message template
        """
        context = {
            "waiting": self.get_waiting_details(status_details),
        }

        return 'openassessmentblock/message/oa_message_complete.html', context

    def render_message_closed(self, status_info):
        """
        Renders the "Closed" message state

        Args:
            status_info (dict): The dictionary describing the closed status of the current step

        Returns:
            The path (String) and context (dict) to render the "Closed" template
        """

        reason = status_info.get("reason")

        context = {
            "not_yet_open": (reason == "start")
        }

        return 'openassessmentblock/message/oa_message_closed.html', context

    def render_message_open(self, deadline_info):
        """
        Renders the "Open" message state

        Args:
            deadline_info (dict): The dictionary of boolean assessment near/closed states

        Returns:
            The path (String) and context (dict) to render the "Open" template
        """

        submission_approaching = deadline_info.get("submission").get("approaching")

        context = {
            "approaching": submission_approaching
        }

        return 'openassessmentblock/message/oa_message_open.html', context

    def _get_deadline_info(self):
        """
        Get detailed information about the standing of all deadlines.

        Args:
            None.

        Returns:
            dict with the following elements
                "submission" : dictionary on submission closure of this^ form
                "general" : dictionary on problem (all elements) closure of this^ form
                "peer": dictionary on peer closure of this^ form  *If Assessment has a Peer Section*
                "self": dictionary on self closure of this^ form  *If Assessment has a Self Section*

                this^ form:
                    "is_closed": (bool) Indicating whether or not that section has closed
                    "reason": (str) The reason that the section is closed (None if !is_closed)
                    "approaching": (bool) Indicates whether or not the section deadline is within a day.
        """

        # Methods which use datetime.deltatime to figure out if a deadline is approaching.
        now = dt.datetime.utcnow().replace(tzinfo=pytz.utc)

        def _is_approaching(date):
            # Determines if the deadline is within one day of now. (Approaching = True if so)
            delta = date - now
            return delta.days == 0

        # problem_info has form (is_closed, reason, start_date, due_date)
        problem_info = self.is_closed()

        # submission_info has form (is_closed, reason, start_date, due_date)
        submission_info = self.is_closed("submission")

        # The information we will always pass on to the user. Adds additional dicts on peer and self if applicable.
        deadline_info = {
            "submission": {
                "is_closed": submission_info[0],
                "reason": submission_info[1],
                "approaching": _is_approaching(submission_info[3])
            },
            "general": {
                "is_closed": problem_info[0],
                "reason": problem_info[1],
                "approaching": _is_approaching(problem_info[3])
            }
        }

        has_training = 'student-training' in self.assessment_steps

        if has_training:
            training_info = self.is_closed("student-training")
            training_dict = {
                "training": {
                    "is_closed": training_info[0],
                    "reason": training_info[1],
                    "approaching": _is_approaching(training_info[3])
                }
            }
            deadline_info.update(training_dict)

        has_peer = 'peer-assessment' in self.assessment_steps

        # peer_info has form (is_closed, reason, start_date, due_date)
        if has_peer:
            peer_info = self.is_closed("peer-assessment")
            peer_dict = {
                "peer": {
                    "is_closed": peer_info[0],
                    "reason": peer_info[1],
                    "approaching": _is_approaching(peer_info[3])
                }
            }
            deadline_info.update(peer_dict)

        has_self = 'self-assessment' in self.assessment_steps

        # self_info has form (is_closed, reason, start_date, due_date)
        if has_self:
            self_info = self.is_closed("self-assessment")
            self_dict = {
                "self": {
                    "is_closed": self_info[0],
                    "reason": self_info[1],
                    "approaching": _is_approaching(self_info[3])
                }
            }
            deadline_info.update(self_dict)

        return deadline_info

    def render_message_no_team(self):
        """
        Render the message when the user is not part of a team in the selected teamset.
        """
        if self.teamset_config:
            teamset_name = self.teamset_config.name
        else:
            teamset_name = '<id ' + self.selected_teamset_id + '>'
        context = {'teamset_name': teamset_name}
        return 'openassessmentblock/message/oa_message_no_team.html', context
