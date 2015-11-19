"""
Page objects for UI-level acceptance tests.
"""

import os

from bok_choy.page_object import PageObject
from bok_choy.promise import EmptyPromise

ORA_SANDBOX_URL = os.environ.get('ORA_SANDBOX_URL')


class PageConfigurationError(Exception):
    """ A page object was not configured correctly. """
    pass


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
            base=ORA_SANDBOX_URL,
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

    def hide_django_debug_tool(self):
        if self.q(css='#djDebug').visible:
            self.q(css='#djHideToolBarButton').click()


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
        self.wait_for_element_visibility("textarea.submission__answer__part__text__value", "Textarea is present")
        self.q(css="textarea.submission__answer__part__text__value").fill(response_text)
        self.submit()
        EmptyPromise(lambda: self.has_submitted, 'Response is completed').fulfill()

    def fill_latex(self, latex_query):
        """
        Fill the latex expression
        Args:
         latex_query (unicode): Latex expression text
        """
        self.wait_for_element_visibility("textarea.submission__answer__part__text__value", "Textarea is present")
        self.q(css="textarea.submission__answer__part__text__value").fill(latex_query)

    def preview_latex(self):
        # Click 'Preview in Latex' button on the page.
        self.q(css="button#submission__preview").click()
        self.wait_for_element_visibility("#preview_content .MathJax", "Verify Preview Latex expression")

    def select_file(self, file_path_name):
        """
        Select a file from local file system for uploading

        Args:
          file_path_name (string): full path and name of the file
        """
        self.wait_for_element_visibility("#submission__answer__upload", "File select button is present")
        self.q(css="#submission__answer__upload").results[0].send_keys(file_path_name)

    def upload_file(self):
        """
        Upload the selected file
        """
        self.wait_for_element_visibility("#file__upload", "Upload button is present")
        self.q(css="#file__upload").click()

    @property
    def latex_preview_button_is_disabled(self):
        """
        Check if 'Preview in Latex' button is disabled

        Returns:
            bool
        """
        preview_latex_button_class = self.q(css="button#submission__preview").attrs('class')[0]
        return 'is--disabled' in preview_latex_button_class

    @property
    def has_submitted(self):
        """
        Check whether the response was submitted successfully.

        Returns:
            bool
        """
        return self.q(css=".step--response.is--complete").is_present()

    @property
    def has_file_error(self):
        """
        Check whether there is an error message for file upload.

        Returns:
            bool
        """
        return self.q(css="div#upload__error > div.message--error").visible

    @property
    def has_file_uploaded(self):
        """
        Check whether file is successfully uploaded

        Returns:
            bool
        """
        return self.q(css="#submission__custom__upload").visible


class AssessmentPage(OpenAssessmentPage):
    """
    Page object representing an "assessment" step in an ORA problem.
    """

    ASSESSMENT_TYPES = ['self-assessment', 'peer-assessment', 'student-training']

    def __init__(self, assessment_type, *args):
        """
        Configure which assessment type this page object represents.

        Args:
            assessment_type: One of the valid assessment types.
            *args: Passed to the base class.

        """
        super(AssessmentPage, self).__init__(*args)
        if assessment_type not in self.ASSESSMENT_TYPES:
            msg = "Invalid assessment type; must choose one: {choices}".format(
                choices=", ".join(self.ASSESSMENT_TYPES)
            )
            raise PageConfigurationError(msg)
        self._assessment_type = assessment_type

    def is_browser_on_page(self):
        css_id = "#openassessment__{assessment_type}".format(
            assessment_type=self._assessment_type
        )
        return self.q(css=css_id).is_present()

    @property
    def is_on_top(self):
        # TODO: On top behavior needs to be better defined. It is defined here more accurately as "near-top".
        # pos = self.browser.get_window_position()
        # return pos['y'] < 100
        # self.wait_for_element_visibility(".chapter.is-open", "Chapter heading is on visible", timeout=10)
        return self.q(css=".chapter.is-open").visible

    def assess(self, options_selected):
        """
        Create an assessment.

        Args:
            options_selected (list of int): list of the indices (starting from 0)
            of each option to select in the rubric.

        Returns:
            AssessmentPage

        Example usage:
        >>> page.assess([0, 2, 1])

        """
        for criterion_num, option_num in enumerate(options_selected):
            sel = "#assessment__rubric__question--{criterion_num}__{option_num}".format(
                criterion_num=criterion_num,
                option_num=option_num
            )
            self.q(css=sel).first.click()
        self.submit()
        return self

    @property
    def response_text(self):
        """
        Retrieve the text of the response shown in the assessment.

        Returns:
            unicode
        """
        css_sel = ".{assessment_type}__display .submission__answer__part__text__value>p".format(
            assessment_type=self._assessment_type
        )
        return u" ".join(self.q(css=css_sel).text)

    def wait_for_complete(self):
        """
        Wait until the assessment step is marked as complete.

        Raises:
            BrokenPromise

        returns:
            AssessmentPage

        """
        EmptyPromise(lambda: self.is_complete, 'Assessment is complete').fulfill()
        return self

    def wait_for_response(self):
        """
        Wait for response text to be available.

        Raises:
            BrokenPromise

        Returns:
            AssessmentPage
        """
        EmptyPromise(
            lambda: len(self.response_text) > 0,
            "Has response text."
        ).fulfill()
        return self

    def wait_for_num_completed(self, num_completed):
        """
        Wait for at least a certain number of assessments
        to be completed.

        Can only be used with peer-assessment and student-training.

        Args:
            num_completed (int): The number of assessments we expect
                to be completed.

        Raises:
            PageConfigurationError
            BrokenPromise

        Returns:
            AssessmentPage

        """
        EmptyPromise(
            lambda: self.num_completed >= num_completed,
            "Completed at least one assessment."
        ).fulfill()
        return self

    @property
    def is_complete(self):
        """
        Check whether the assessment was submitted successfully.

        Returns:
            bool
        """
        css_sel = ".step--{assessment_type}.is--complete".format(
            assessment_type=self._assessment_type
        )
        return self.q(css=css_sel).is_present()

    @property
    def num_completed(self):
        """
        Retrieve the number of completed assessments.
        Can only be used for peer-assessment and student-training.

        Returns:
            int

        Raises:
            PageConfigurationError

        """
        if self._assessment_type not in ['peer-assessment', 'student-training']:
            msg = "Only peer assessment and student training steps can retrieve the number completed"
            raise PageConfigurationError(msg)
        candidates = [int(x) for x in self.q(css=".step__status__value--completed").text]
        return candidates[0] if len(candidates) > 0 else None


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


class StaffAreaPage(OpenAssessmentPage):
    """
    Page object representing the "submission" step in an ORA problem.
    """

    def is_browser_on_page(self):
        return self.q(css="#openassessment__staff-area").is_present()

    @property
    def selected_button_names(self):
        """
        Returns the names of the selected toolbar buttons.
        """
        buttons = self.q(css=".ui-staff__button")
        return [button.text for button in buttons if u'is--active' in button.get_attribute('class')]

    @property
    def visible_staff_panels(self):
        """
        Returns the ids of the visible staff panels
        """
        panels = self.q(css=".wrapper--ui-staff")
        return [panel.get_attribute('id') for panel in panels if u'is--hidden' not in panel.get_attribute('class')]

    def click_staff_toolbar_button(self, button_name):
        """
        Presses the button to show the panel with the specified name.
        :return:
        """
        buttons = self.q(css=".button-{button_name}".format(button_name=button_name))
        buttons.first.click()

    def click_staff_panel_close_button(self, panel_name):
        """
        Presses the close button on the staff panel with the specified name.
        :return:
        """
        self.q(css=".wrapper--{panel_name} .ui-staff_close_button".format(panel_name=panel_name)).click()
