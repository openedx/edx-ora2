"""
Performance tests for the OpenAssessment XBlock.
"""

import os
import json
import random
from lxml import etree
import loremipsum
from locust import HttpLocust, TaskSet, task


class OpenAssessmentPage(object):
    """
    Encapsulate interactions with the OpenAssessment XBlock's pages.
    """

    # These assume that the course fixture has been installed
    COURSE_ID = "tim/1/1"
    BASE_URL = "courses/tim/1/1/courseware/efa85eb090164a208d772a344df7181d/69f15a02c5af4e95b9c5525771b8f4ee/"
    BASE_HANDLER_URL = "courses/tim/1/1/xblock/i4x:;_;_tim;_1;_openassessment;_0e2bbf6cc89e45d98b028fa4e2d46314/handler/"
    OPTIONS_SELECTED = {
        "Ideas": "Good",
        "Content": "Excellent",
    }

    def __init__(self, client):
        """
        Initialize the page to use specified HTTP client.

        Args:
            client (HttpSession): The HTTP client to use.
        """
        self.client = client

        # Configure basic auth
        if 'BASIC_AUTH_USER' in os.environ and 'BASIC_AUTH_PASSWORD' in os.environ:
            self.client.auth = (os.environ['BASIC_AUTH_USER'], os.environ['BASIC_AUTH_PASSWORD'])

        self.step_resp_dict = dict()

    def log_in(self):
        """
        Log in as a unique user with access to the XBlock(s) under test.
        """
        self.client.get("auto_auth", params={'course_id': self.COURSE_ID}, verify=False)
        return self

    def load_steps(self):
        """
        Load all steps in the OpenAssessment flow.
        """
        # Load the container page
        self.client.get(self.BASE_URL, verify=False)

        # Load each of the steps
        step_dict = {
            'submission': 'render_submission',
            'peer': 'render_peer_assessment',
            'self': 'render_self_assessment',
            'grade': 'render_grade',
        }

        self.step_resp_dict = {
            name: self.client.get(self.handler_url(handler), verify=False)
            for name, handler in step_dict.iteritems()
        }

        return self

    def can_submit_response(self):
        """
        Check whether we're allowed to submit a response.
        Should be called after steps have been loaded.

        Returns:
            bool
        """
        resp = self.step_resp_dict.get('submission')
        return resp is not None and resp.content is not None and 'id="submission__answer__value"' in resp.content.lower()

    def can_peer_assess(self):
        """
        Check whether we're allowed to assess a peer.
        Should be called after steps have been loaded.

        Returns:
            bool
        """
        resp = self.step_resp_dict.get('peer')
        return resp is not None and resp.content is not None and 'class="assessment__fields"' in resp.content.lower()

    def can_self_assess(self):
        """
        Check whether we're allowed to self-assess.
        Should be called after steps have been loaded.

        Returns:
            bool
        """
        resp = self.step_resp_dict.get('self')
        return resp is not None and resp.content is not None and 'class="assessment__fields"' in resp.content.lower()

    def has_grade(self):
        """
        Check whether the user has a grade.

        Returns:
            bool
        """
        resp = self.step_resp_dict.get('grade')
        return resp is not None and resp.content is not None and "has--grade" in resp.content.lower()

    def submit_response(self):
        """
        Submit a response.
        """
        payload = json.dumps({
            'submission': loremipsum.get_paragraphs(random.randint(1, 10)),
        })
        self.client.post(self.handler_url('submit'), data=payload, headers=self._post_headers, verify=False)

    def peer_assess(self):
        """
        Assess a peer.
        """
        payload = json.dumps({
            'submission_uuid': self._submission_uuid('peer'),
            'options_selected': self.OPTIONS_SELECTED,
            'feedback': loremipsum.get_paragraphs(random.randint(1, 3)),
        })
        self.client.post(self.handler_url('peer_assess'), data=payload, headers=self._post_headers, verify=False)

    def self_assess(self):
        """
        Complete a self-assessment.
        """
        payload = json.dumps({
            'submission_uuid': self._submission_uuid('self'),
            'options_selected': self.OPTIONS_SELECTED,
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
        return "{base}{handler}".format(base=self.BASE_HANDLER_URL, handler=handler_name)

    def _submission_uuid(self, step):
        """
        Retrieve the submission UUID from the DOM.

        Args:
            step (str): Either "peer" or "self"

        Returns:
            str or None
        """
        resp = self.step_resp_dict.get(step)
        if resp is None:
            return None

        # There might be a faster way to do this
        root = etree.fromstring(resp.content)
        xpath_sel = "span[@id=\"{step}_submission_uuid\"]".format(step=step)
        submission_id_el = root.find(xpath_sel)
        if submission_id_el is not None:
            return submission_id_el.text.strip()
        else:
            return None

    @property
    def _post_headers(self):
        """
        Headers for a POST request, including the CSRF token.
        """
        return {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': self.client.cookies.get('csrftoken', ''),
        }


class OpenAssessmentTasks(TaskSet):
    """
    Virtual user interactions with the OpenAssessment XBlock.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the task set.
        """
        super(OpenAssessmentTasks, self).__init__(*args, **kwargs)
        self.page = OpenAssessmentPage(self.client)

    def on_start(self):
        """
        Log in as a unique user.
        """
        self.page.log_in()

    @task
    def workflow(self):
        """
        Submit a response, if we're allowed to.
        """
        self.page.load_steps()

        if self.page.can_submit_response():
            self.page.submit_response()

        if self.page.can_peer_assess():
            self.page.peer_assess()

        if self.page.can_self_assess():
            self.page.self_assess()

        # At the end of the workflow, log in as a new user
        # so we can continue to make new submissions
        if self.page.has_grade():
            self.page.log_in()


class OpenAssessmentLocust(HttpLocust):
    """
    Performance test definition for the OpenAssessment XBlock.
    """
    task_set = OpenAssessmentTasks
    min_wait = 10000
    max_wait = 15000
