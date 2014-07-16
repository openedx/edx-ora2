"""
Page objects for UI-level acceptance tests.
"""
from bok_choy.page_object import PageObject
from bok_choy.promise import EmptyPromise

import os
BASE_URL = os.environ.get('BASE_URL')
assert BASE_URL is not None, 'No base URL specified - please set the `BASE_URL` environment variable'


class OpenAssessmentPage(PageObject):
    """
    Base class for ORA page objects.
    """

    def __init__(self, browser, problem_location):
        """
        Configure a page object for a particular ORA problem.

        Args:
            browser (Selenium browser): The browser object used by the tests.
            problem_location (unicode): URL path for the problem, appended to the base URL.

        """
        super(OpenAssessmentPage, self).__init__(browser)
        self._problem_location = problem_location

    @property
    def url(self):
        return "{base}/{loc}".format(
            base=BASE_URL,
            loc=self._problem_location
        )

    def submit(self):
        """
        Click the submit button on the page.
        This relies on the fact that we use the same CSS styles for submit buttons
        in all problem steps.
        """
        EmptyPromise(
            lambda: 'is--disabled' not in " ".join(self.q(css=".action--submit").attrs('class')),
            "Submit button is enabled."
        ).fulfill()

        with self.handle_alert():
            self.q(css=".action--submit").first.click()


class SubmissionPage(OpenAssessmentPage):
    """
    Page object representing the "submission" step in an ORA problem.
    """

    def is_browser_on_page(self):
        return self.q(css='#openassessment__response').is_present()

    def submit_response(self, response_text):
        """
        Submit a response for the problem.

        Args:
            response_text (unicode): The submission response text.

        Raises:
            BrokenPromise: The response was not submitted successfully.

        """
        self.q(css="textarea#submission__answer__value").fill(response_text)
        self.submit()
        EmptyPromise(lambda: self.has_submitted, 'Response is completed').fulfill()

    @property
    def has_submitted(self):
        """
        Check whether the response was submitted successfully.

        Returns:
            bool
        """
        return self.q(css=".step--response.is--complete").is_present()


class SelfAssessmentPage(OpenAssessmentPage):
    """
    Page object representing the "self assessment" step in an ORA problem.
    """

    def is_browser_on_page(self):
        return self.q(css="#openassessment__self-assessment").is_present()

    def assess(self, options_selected):
        """
        Create a self-assessment.

        Args:
            options_selected (list of int): list of the indices (starting from 0)
            of each option to select in the rubric.

        Example usage:
        >>> self_page.assess([0, 2, 1])

        """
        for criterion_num, option_num in enumerate(options_selected):
            sel = "#assessment__rubric__question--{criterion_num}__{option_num}".format(
                criterion_num=criterion_num,
                option_num=option_num
            )
            self.q(css=sel).first.click()
        self.submit()
        EmptyPromise(lambda: self.has_submitted, 'Self assessment is complete').fulfill()

    @property
    def response_text(self):
        """
        Retrieve the text of the response shown in the assessment.

        Returns:
            unicode
        """
        return u" ".join(self.q(css=".self-assessment__display__response>p").text)

    @property
    def has_submitted(self):
        """
        Check whether the assessment was submitted successfully.

        Returns:
            bool
        """
        return self.q(css=".step--self-assessment.is--complete").is_present()


class GradePage(OpenAssessmentPage):
    """
    Page object representing the "grade" step in an ORA problem.
    """

    def is_browser_on_page(self):
        return self.q(css="#openassessment__grade").is_present()

    @property
    def score(self):
        """
        Retrieve the number of points received.

        Returns:
            int or None

        Raises:
            ValueError if the score is not an integer.
        """
        score_candidates = [int(x) for x in self.q(css=".grade__value__earned").text]
        return score_candidates[0] if len(score_candidates) > 0 else None
