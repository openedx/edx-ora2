# -*- coding: utf-8 -*-
"""
Base class for handler-level testing of the XBlock.
"""
from __future__ import absolute_import, print_function

import copy
from functools import wraps
import json
import os.path

import mock
from six.moves import zip

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.test_utils import CacheResetTest, TransactionCacheResetTest
from openassessment.workflow import api as workflow_api
from submissions import api as submissions_api
import webob
from workbench.runtime import WorkbenchRuntime

# Sample peer assessments
PEER_ASSESSMENTS = [
    {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Good'},
        'criterion_feedback': {
            u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!'
        },
        'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
    },
    {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Ġööḋ', u'Form': u'Fair'},
        'criterion_feedback': {
            u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
            u'Form': u'Peer 2: ƒαιя נσв'
        },
        'overall_feedback': u'Good job!',
    },
]

# Sample self assessment
SELF_ASSESSMENT = {
    'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
    'criterion_feedback': {
        u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!'
    },
    'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
}

# A sample good staff assessment
STAFF_GOOD_ASSESSMENT = {
    'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
    'criterion_feedback': {
        u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Staff: ฝﻉɭɭ ɗѻกﻉ!',
        u'Form': u'Staff: ƒαιя נσв'
    },
    'overall_feedback': u'Staff: good job!',
    'assess_type': 'full-grade'
}

# A sample bad staff assessment
STAFF_BAD_ASSESSMENT = {
    'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ק๏๏г', u'Form': u'Poor'},
    'criterion_feedback': {
        u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Staff: ק๏๏г נσв',
        u'Form': u'Staff: ק๏๏г נσв'
    },
    'overall_feedback': u'Staff: very poor',
    'assess_type': 'full-grade'
}


def scenario(scenario_path, user_id=None):
    """
    Method decorator to load a scenario for a test case.
    Must be called on an `XBlockHandlerTestCase` subclass, or
    else it will have no effect.

    Args:
        scenario_path (str): Path to the scenario XML file.

    Keyword Arguments:
        user_id (str or None): User ID to log in as, or None.

    Returns:
        The decorated method

    Example:

        @scenario('data/test_scenario.xml')
        def test_submit(self, xblock):
            response = self.request(xblock, 'submit', 'Test submission')
            self.assertTrue('Success' in response)
    """
    def _decorator(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):

            # Retrieve the object (self)
            # if this is a function, not a method, then do nothing.
            xblock = None
            if args:
                self = args[0]
                if isinstance(self, XBlockHandlerTestCaseMixin):

                    # Print a debug message
                    print("Loading scenario from {path}".format(path=scenario_path))

                    # Configure the runtime with our user id
                    self.set_user(user_id)

                    # Load the scenario
                    xblock = self.load_scenario(scenario_path)

                    # Pass the XBlock as the first argument to the decorated method (after `self`)
                    args = list(args)
                    args.insert(1, xblock)

            return func(*args, **kwargs)
        return _wrapped
    return _decorator


class XBlockHandlerTestCaseMixin(object):
    """
    Load the XBlock in the workbench runtime to test its handler.
    """

    def setUp(self):
        """
        Create the runtime.
        """
        super(XBlockHandlerTestCaseMixin, self).setUp()
        self.runtime = WorkbenchRuntime()
        mock_publish = mock.MagicMock(side_effect=self.runtime.publish)
        self.runtime.publish = mock_publish

    def set_user(self, user_id):
        """
        Provide a user ID to the runtime.

        Args:
            user_id (str): a user ID.

        Returns:
            None
        """
        self.runtime.user_id = user_id

    def load_scenario(self, xml_path):
        """
        Load an XML definition of an XBlock and return the XBlock instance.

        Args:
            xml (string): Path to an XML definition of the XBlock, relative
                to the test module.

        Returns:
            XBlock
        """
        block_id = self.runtime.parse_xml_string(
            self.load_fixture_str(xml_path), self.runtime.id_generator
        )
        return self.runtime.get_block(block_id)

    def request(self, xblock, handler_name, content, request_method="POST", response_format=None, use_runtime=True):
        """
        Make a request to an XBlock handler.

        Args:
            xblock (XBlock): The XBlock instance that should handle the request.
            handler_name (str): The name of the handler.
            content (unicode): Content of the request.

        Keyword Arguments:
            request_method (str): The HTTP method of the request (defaults to POST)
            response_format (None or str): Expected format of the response string.
                If `None`, return the raw response content; if 'json', parse the
                response as JSON and return the result.

        Raises:
            NotImplementedError: Response format not supported.

        Returns:
            Content of the response (mixed).
        """
        # Create a fake request
        request = webob.Request(dict())
        request.method = request_method
        request.body = content

        # Send the request to the XBlock handler
        if use_runtime:
            response = self.runtime.handle(xblock, handler_name, request)
        else:
            response = getattr(xblock, handler_name)(request)

        # Parse the response (if a format is specified)
        if response_format is None:
            return response.body
        elif response_format == 'json':
            return json.loads(response.body)
        else:
            raise NotImplementedError("Response format '{format}' not supported".format(response_format))

    def assert_assessment_event_published(self, xblock, event_name, assessment, **kwargs):
        parts_list = []
        for part in assessment["parts"]:
            # Some assessment parts do not include point values,
            # only written feedback.  In this case, the assessment
            # part won't have an associated option.
            option_dict = None
            if part["option"] is not None:
                option_dict = {
                    "name": part["option"]["name"],
                    "points": part["option"]["points"],
                }

            # All assessment parts are associated with criteria
            criterion_dict = {
                "name": part["criterion"]["name"],
                "points_possible": part["criterion"]["points_possible"]
            }

            parts_list.append({
                "option": option_dict,
                "criterion": criterion_dict,
                "feedback": part["feedback"]
            })

        event_data = {
            "feedback": assessment["feedback"],
            "rubric": {
                "content_hash": assessment["rubric"]["content_hash"],
            },
            "scorer_id": assessment["scorer_id"],
            "score_type": assessment["score_type"],
            "scored_at": assessment["scored_at"],
            "submission_uuid": assessment["submission_uuid"],
            "parts": parts_list
        }

        for key in kwargs:
            event_data[key] = kwargs[key]

        self.assert_event_published(
            xblock, event_name, event_data
        )

    def assert_event_published(self, xblock, event_name, event_data):
        """
        Assert that an event was emitted with the given parameters.
        Args:
            event_name(str): The name of the event emitted
            event_data(dict): A dictionary containing the data we expect to have publish
        """
        self.runtime.publish.assert_any_call(
            xblock, event_name, event_data
        )

    @staticmethod
    def load_fixture_str(path):
        """
        Load data from a fixture file.

        Args:
            path (str): Path to the file.

        Returns:
            unicode: contents of the file.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, path)) as file_handle:
            return file_handle.read()


class XBlockHandlerTestCase(XBlockHandlerTestCaseMixin, CacheResetTest):
    """
    Base XBlock handler test case.  Use this if you do NOT need to simulate the read-replica.
    """
    pass


class XBlockHandlerTransactionTestCase(XBlockHandlerTestCaseMixin, TransactionCacheResetTest):
    """
    Variation of the XBlock handler test case that truncates the test database instead
    of rolling back transactions.  This is necessary if the software under test relies
    on the read replica.  It's also slower, so unless you're using the read-replica,
    use `XBlockHandlerTestCase` instead.
    """
    pass


class SubmitAssessmentsMixin(object):
    """
    A mixin for creating a submission and peer/self assessments so that the user can
    receive a grade. This is useful for getting into the "waiting for peer assessment" state.
    """
    maxDiff = None

    PEERS = ['McNulty', 'Moreland']

    SUBMISSION = (u'ՇﻉรՇ', u'รપ๒๓ٱรรٱѻก')

    STEPS = ['peer', 'self']

    def create_submission_and_assessments(
            self, xblock, submission_text, peers, peer_assessments, self_assessment,
            waiting_for_peer=False,
    ):
        """
        Create a submission and peer/self assessments, so that the user can receive a grade.

        Args:
            xblock (OpenAssessmentBlock): The XBlock, loaded for the user who needs a grade.
            submission_text (unicode): Text of the submission from the user.
            peers (list of unicode): List of user IDs of peers who will assess the user.
            peer_assessments (list of dict): List of assessment dictionaries for peer assessments.
            self_assessment (dict): Dict of assessment for self-assessment.

        Keyword Arguments:
            waiting_for_peer (bool): If true, skip creation of peer assessments for the user's submission.

        Returns:
            the submission

        """
        # Create a submission from the user
        student_item = xblock.get_student_item_dict()
        student_id = student_item['student_id']
        submission = xblock.create_submission(student_item, submission_text)

        if len(peers) > 0:
            # Create submissions and (optionally) assessments from other users
            must_be_graded_by = xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
            scorer_subs = self.create_peer_submissions(student_item, peers, submission_text)
            if not waiting_for_peer:
                for scorer_sub, scorer_name, assessment in zip(scorer_subs, peers, peer_assessments):
                    self.create_peer_assessment(
                        scorer_sub,
                        scorer_name,
                        submission,
                        assessment,
                        xblock.rubric_criteria,
                        must_be_graded_by
                    )

            # Have our user make assessments (so she can get a score)
            for i, assessment in enumerate(peer_assessments):
                self.create_peer_assessment(
                    submission,
                    student_id,
                    scorer_subs[i],
                    assessment,
                    xblock.rubric_criteria,
                    must_be_graded_by
                )

        # Have the user submit a self-assessment (so she can get a score)
        if self_assessment is not None:
            self.create_self_assessment(submission, student_id, self_assessment, xblock.rubric_criteria)

        return submission

    def create_peer_submissions(self, student_item, peer_names, submission_text):
        """Create len(peer_names) submissions, and return them."""
        returned_subs = []
        for peer in peer_names:
            scorer = copy.deepcopy(student_item)
            scorer['student_id'] = peer

            scorer_sub = submissions_api.create_submission(scorer, {'text': submission_text})
            returned_subs.append(scorer_sub)
            workflow_api.create_workflow(scorer_sub['uuid'], self.STEPS)
        return returned_subs

    def create_peer_assessment(self, scorer_sub, scorer, sub_to_assess, assessment, criteria, grading_requirements):
        """Create a peer assessment of submission sub_to_assess by scorer."""
        peer_api.create_peer_workflow_item(scorer_sub['uuid'], sub_to_assess['uuid'])
        peer_api.create_assessment(
            scorer_sub['uuid'],
            scorer,
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': criteria},
            grading_requirements
        )

    def create_self_assessment(self, submission, student_id, assessment, criteria):
        """Submit a self assessment using the information given."""
        self_api.create_assessment(
            submission['uuid'],
            student_id,
            assessment['options_selected'],
            assessment['criterion_feedback'],
            assessment['overall_feedback'],
            {'criteria': criteria}
        )

    @staticmethod
    def set_staff_access(xblock):
        xblock.xmodule_runtime = mock.Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = 'Bob'

    @staticmethod
    def set_mock_workflow_info(xblock, workflow_status, status_details, submission_uuid):
        xblock.get_workflow_info = mock.Mock(return_value={
            'status': workflow_status,
            'status_details': status_details,
            'submission_uuid': submission_uuid
        })

    def submit_staff_assessment(self, xblock, submission, assessment):
        """
        Submits a staff assessment for the specified submission.

        Args:
            xblock: The XBlock being assessed.
            submission: The submission being assessed.
            assessment: The staff assessment.
        """
        self.set_staff_access(xblock)
        assessment = copy.deepcopy(assessment)
        assessment['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'staff_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])
