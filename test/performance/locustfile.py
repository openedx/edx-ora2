"""
Performance tests for the OpenAssessment XBlock.
"""

import os
import json
import random
from collections import namedtuple
import gevent
import loremipsum
from locust import HttpLocust, TaskSet, task



class OpenAssessmentPage(object):
    """
    Encapsulate interactions with the OpenAssessment XBlock's pages.
    """

    # These assume that the course fixture has been installed
    ProblemFixture = namedtuple('ProblemFixture', [
        'course_id', 'base_url', 'base_handler_url',
        'rubric_options', 'render_step_handlers'
    ])

    PROBLEMS = {
        'peer_then_self': ProblemFixture(
            course_id="ora2/1/1",
            base_url= "courses/ora2/1/1/courseware/efa85eb090164a208d772a344df7181d/69f15a02c5af4e95b9c5525771b8f4ee/",
            base_handler_url="courses/ora2/1/1/xblock/i4x:;_;_ora2;_1;_openassessment;_0e2bbf6cc89e45d98b028fa4e2d46314/handler/",
            rubric_options={
                'Ideas': ['Poor', 'Fair', 'Good'],
                'Content': ['Poor', 'Fair', 'Good', 'Excellent']
            },
            render_step_handlers=[
                'render_submission', 'render_peer_assessment',
                'render_self_assessment', 'render_grade',
            ]
        ),

        'example_based': ProblemFixture(
            course_id="ora2/1/1",
            base_url="courses/ora2/1/1/courseware/efa85eb090164a208d772a344df7181d/fb039ef8a34641509190918ada79122a/",
            base_handler_url="courses/ora2/1/1/xblock/i4x:;_;_ora2;_1;_openassessment;_8df3fa4de26747e0ad99b4157e45f5e5/handler/",
            rubric_options={
                'Ideas': ['Bad', 'Good'],
                'Content': ['Bad', 'Good']
            },
            render_step_handlers=['render_submission', 'render_grade']
        )
    }

    def __init__(self, hostname, client, problem_name):
        """
        Initialize the page to use specified HTTP client.

        Args:
            hostname (unicode): The hostname (used for the referer HTTP header)
            client (HttpSession): The HTTP client to use.
            problem_name (unicode): Name of the problem (one of the keys in `OpenAssessmentPage.PROBLEMS`)

        """
        self.hostname = hostname
        self.client = client
        self.problem_fixture = self.PROBLEMS[problem_name]
        self.logged_in = False

        # Configure basic auth
        if 'BASIC_AUTH_USER' in os.environ and 'BASIC_AUTH_PASSWORD' in os.environ:
            self.client.auth = (os.environ['BASIC_AUTH_USER'], os.environ['BASIC_AUTH_PASSWORD'])

    def log_in(self):
        """
        Log in as a unique user with access to the XBlock(s) under test.
        """
        resp = self.client.get("auto_auth", params={'course_id': self.problem_fixture.course_id}, verify=False)
        self.logged_in = (resp.status_code == 200)
        return self

    def load_steps(self):
        """
        Load all steps in the OpenAssessment flow.
        """
        # Load the container page
        self.client.get(self.problem_fixture.base_url, verify=False)

        # Load each of the steps in parallel
        get_unverified = lambda url: self.client.get(url, verify=False)
        gevent.joinall([
            gevent.spawn(get_unverified, url) for url in [
                self.handler_url(handler)
                for handler in self.problem_fixture.render_step_handlers
            ]
        ], timeout=0.5)

        return self

    def submit_response(self):
        """
        Submit a response.
        """
        payload = json.dumps({
            'submission': u' '.join(loremipsum.get_paragraphs(random.randint(1, 10))),
        })
        self.client.post(self.handler_url('submit'), data=payload, headers=self._post_headers, verify=False)

    def peer_assess(self, continue_grading=False):
        """
        Assess a peer.

        Kwargs:
            continue_grading (bool): If true, simulate "continued grading"
                in which a student asks to assess peers in addition to the required number.

        """
        params = {
            'options_selected': self._select_random_options(),
            'overall_feedback': loremipsum.get_paragraphs(random.randint(1, 3)),
            'criterion_feedback': {}
        }

        if continue_grading:
            params['continue_grading'] = True

        payload = json.dumps(params)
        self.client.post(self.handler_url('peer_assess'), data=payload, headers=self._post_headers, verify=False)

    def self_assess(self):
        """
        Complete a self-assessment.
        """
        payload = json.dumps({
            'options_selected': self._select_random_options()
        })
        self.client.post(self.handler_url('self_assess'), data=payload, headers=self._post_headers, verify=False)

    def handler_url(self, handler_name):
        """
        Return the full URL for an XBlock handler.

        Args:
            handler_name (str): The name of the XBlock handler method.

        Returns:
            str
        """
        return "{base}{handler}".format(base=self.problem_fixture.base_handler_url, handler=handler_name)

    def _select_random_options(self):
        """
        Select random options for each criterion in the rubric.
        """
        return {
            criterion: random.choice(options)
            for criterion, options in self.problem_fixture.rubric_options.iteritems()
        }

    @property
    def _post_headers(self):
        """
        Headers for a POST request, including the CSRF token.
        """
        return {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': self.client.cookies.get('csrftoken', ''),
            'Referer': self.hostname
        }


class OpenAssessmentTasks(TaskSet):
    """
    Virtual user interactions with the OpenAssessment XBlock.
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=W0613
        """
        Initialize the task set.
        """
        super(OpenAssessmentTasks, self).__init__(*args, **kwargs)
        self.hostname = self.locust.host
        self.page = None

    @task
    def peer_and_self(self):
        """
        Test the peer-->self workflow.
        """
        if self.page is None:
            self.page = OpenAssessmentPage(self.hostname, self.client, 'peer_then_self')  # pylint: disable=E1101
            self.page.log_in()

        if not self.page.logged_in:
            self.page.log_in()
        else:
            self._submit_response()

            # Randomly peer/self assess or log in as a new user.
            # This should be sufficient to get students through
            # the entire flow (satisfying the requirements for peer assessment).
            action = random.randint(0, 100)
            if action <= 80:
                continue_grading = random.randint(0, 10) < 4
                self.page.peer_assess(continue_grading=continue_grading)
                self.page.self_assess()
            else:
                self.page.log_in()

    @task
    def example_based(self):
        """
        Test example-based assessment only.
        """
        if self.page is None:
            self.page = OpenAssessmentPage(self.hostname, self.client, 'example_based')  # pylint: disable=E1101
            self.page.log_in()

        if not self.page.logged_in:
            self.page.log_in()
        else:
            self._submit_response()
            if random.randint(0, 100) < 50:
                self.page.log_in()

    def _submit_response(self):
        """
        Simulate the user loading the page, submitting a response,
        then reloading the steps (usually triggered by AJAX).
        If the user has already submitted, the handler will return
        an error message in the JSON, but the HTTP status will still be 200.
        """
        self.page.load_steps()
        self.page.submit_response()
        self.page.load_steps()


class OpenAssessmentLocust(HttpLocust):
    """
    Performance test definition for the OpenAssessment XBlock.
    """
    task_set = OpenAssessmentTasks
    min_wait = 10000
    max_wait = 15000
