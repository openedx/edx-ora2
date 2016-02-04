"""
Performance test utility for the OpenAssessment XBlock.
"""

import os
import json
import random
from collections import namedtuple
import gevent
import loremipsum


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
            course_id="course-v1:edx+ORA203+course",
            base_url="courses/course-v1:edx+ORA203+course/xblock/block-v1:edx+ORA203+course+type@openassessment+block@47dc34e528f441f493db14a2cbdfa8b9/",
            base_handler_url="courses/course-v1:edx+ORA203+course/xblock/block-v1:edx+ORA203+course+type@openassessment+block@47dc34e528f441f493db14a2cbdfa8b9/handler/",
            rubric_options={
                'Ideas': ['Poor', 'Fair', 'Good'],
                'Content': ['Poor', 'Fair', 'Good', 'Excellent']
            },
            render_step_handlers=[
                'render_submission', 'render_peer_assessment',
                'render_self_assessment', 'render_grade',
            ]
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
        resp = self.client.get(
            "auto_auth",
            params={'course_id': self.problem_fixture.course_id},
            verify=False,
            timeout=120
        )
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
            'submission': [u' '.join(loremipsum.get_sentence())],
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
