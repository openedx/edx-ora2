"""
Auto-auth page (used to automatically log in during testing).
"""
import json
import os
import re
import urllib

from bok_choy.page_object import PageObject

ORA_SANDBOX_URL = os.environ.get('ORA_SANDBOX_URL')


class AutoAuthPage(PageObject):
    """
    The automatic authorization page.
    When allowed via the django settings file, visiting
    this url will create a user and log them in.
    """

    def __init__(self, browser, username=None, email=None, password=None, staff=None, course_id=None, roles=None):
        """
        Auto-auth is an end-point for HTTP GET requests.
        By default, it will create accounts with random user credentials,
        but you can also specify credentials using querystring parameters.

        `username`, `email`, and `password` are the user's credentials (strings)
        `staff` is a boolean indicating whether the user is global staff.
        `course_id` is the ID of the course to enroll the student in.
        Currently, this has the form "org/number/run"

        Note that "global staff" is NOT the same as course staff.
        """
        super(AutoAuthPage, self).__init__(browser)

        # Create query string parameters if provided
        self._params = {}

        if username is not None:
            self._params['username'] = username

        if email is not None:
            self._params['email'] = email

        if password is not None:
            self._params['password'] = password

        if staff is not None:
            self._params['staff'] = "true" if staff else "false"

        if course_id is not None:
            self._params['course_id'] = course_id

        if roles is not None:
            self._params['roles'] = roles

        self.data = {}

    @property
    def url(self):
        """
        Construct the URL.
        """
        url = ORA_SANDBOX_URL + "/auto_auth"
        query_str = urllib.urlencode(self._params)

        if query_str:
            url += "?" + query_str

        return url

    def is_browser_on_page(self):
        self.data = json.loads(self.q(css='BODY').text[0])
        return self.data['created_status'] == "Logged in"

    def get_user_id(self):
        """
        Finds and returns the user_id
        """
        return self.data['user_id']

    def get_username_and_email(self):
        """
        Finds and returns the username and email address of the current user.
        """
        return self.data['username'], self.data['email']
