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

    def _bounded_selector(self, selector):
        """
        Allows scoping to a portion of the page.

        The default implementation just returns the selector
        """
        return selector

    @property
    def url(self):
        return "{base}/{loc}".format(
            base=ORA_SANDBOX_URL,
            loc=self._problem_location
        )

    def submit(self, button_css=".action--submit"):
        """
        Click the submit button on the page.
        This relies on the fact that we use the same CSS styles for submit buttons
        in all problem steps (unless custom value for button_css is passed in).
        """
        EmptyPromise(
            lambda: 'is--disabled' not in " ".join(self.q(css=self._bounded_selector(button_css)).attrs('class')),
            "Submit button is enabled."
        ).fulfill()

        with self.handle_alert():
            self.q(css=self._bounded_selector(button_css)).first.click()

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


class AssessmentMixin(object):
    """
    Mixin for interacting with the assessment rubric.
    """
    def assess(self, assessment_type, options_selected):
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
            sel = "#{assessment_type}__assessment__rubric__question--{criterion_num}__{option_num}".format(
                assessment_type=assessment_type,
                criterion_num=criterion_num,
                option_num=option_num
            )
            self.q(css=self._bounded_selector(sel)).first.click()
        self.submit_assessment()
        return self

    def submit_assessment(self):
        """
        Submit an assessment of the problem.
        """
        self.submit()


class AssessmentPage(OpenAssessmentPage, AssessmentMixin):
    """
    Page object representing an "assessment" step in an ORA problem.
    """

    ASSESSMENT_TYPES = ['self-assessment', 'peer-assessment', 'student-training', 'staff-assessment']

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

    def _bounded_selector(self, selector):
        """
        Return `selector`, but limited to this Assignment Page.
        """
        return '#openassessment__{assessment_type} {selector}'.format(
            assessment_type=self._assessment_type, selector=selector)

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

    @property
    def label(self):
        """
        Returns the label of this assessment step.

        Returns:
            string
        """
        return self.q(css=self._bounded_selector(".step__label")).text[0]

    @property
    def status_value(self):
        """
        Returns the status value (ie., "COMPLETE", "CANCELLED", etc.) of this assessment step.

        Returns:
            string
        """
        return self.q(css=self._bounded_selector(".step__status__value")).text[0]

    @property
    def message_title(self):
        """
        Returns the message title, if present, of this assesment step.

        Returns:
            string is message title is present, else None
        """
        message_title = self.q(css=self._bounded_selector(".message__title"))
        if len(message_title) == 0:
            return None
        return message_title.text[0]

    def verify_status_value(self, expected_value):
        """
        Waits until the expected status value appears. If it does not appear, fails the test.
        """
        EmptyPromise(
            lambda: self.status_value == expected_value,
            "Expected status value present"
        ).fulfill()


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

    def grade_entry(self, question, column):
        """
        Returns a tuple of source and value information for a specific grade source.

        Args:
            question: the 0-based question for which to get grade information.
            column: the 0-based column of data within a question. Each column corresponds
                to a source of data (for example, staff, peer, or self).

        Returns: the tuple of source and value information for the requested grade

        """
        source = self.q(
            css=self._bounded_selector('.question--{} .answer .answer__source__value'.format(question + 1))
        )[column]

        value = self.q(
            css=self._bounded_selector('.question--{} .answer .answer__value__value'.format(question + 1))
        )[column]

        return source.text.strip(), value.text.strip()


class StaffAreaPage(OpenAssessmentPage, AssessmentMixin):
    """
    Page object representing the tabbed staff area.
    """

    def _bounded_selector(self, selector):
        """
        Return `selector`, but limited to the staff area management area.
        """
        return '.openassessment__staff-area {}'.format(selector)

    def is_browser_on_page(self):
        return self.q(css=".openassessment__staff-area").is_present()

    @property
    def selected_button_names(self):
        """
        Returns the names of the selected toolbar buttons.
        """
        buttons = self.q(css=self._bounded_selector(".ui-staff__button"))
        return [button.text for button in buttons if u'is--active' in button.get_attribute('class')]

    @property
    def visible_staff_panels(self):
        """
        Returns the classes of the visible staff panels
        """
        panels = self.q(css=self._bounded_selector(".wrapper--ui-staff"))
        return [panel.get_attribute('class') for panel in panels if u'is--hidden' not in panel.get_attribute('class')]

    def is_button_visible(self, button_name):
        """
        Returns True if button_name is visible, else False
        """
        button = self.q(css=self._bounded_selector(".button-{button_name}".format(button_name=button_name)))
        return button.is_present()

    def click_staff_toolbar_button(self, button_name):
        """
        Presses the button to show the panel with the specified name.
        :return:
        """
        buttons = self.q(css=self._bounded_selector(".button-{button_name}".format(button_name=button_name)))
        buttons.first.click()

    def click_staff_panel_close_button(self, panel_name):
        """
        Presses the close button on the staff panel with the specified name.
        :return:
        """
        self.q(
            css=self._bounded_selector(".wrapper--{panel_name} .ui-staff_close_button".format(panel_name=panel_name))
        ).click()

    def show_learner(self, username):
        """
        Clicks the staff tools panel and and searches for learner information about the given username.
        """
        self.click_staff_toolbar_button("staff-tools")
        student_input_css = self._bounded_selector("input.openassessment__student_username")
        self.wait_for_element_visibility(student_input_css, "Input is present")
        self.q(css=student_input_css).fill(username)
        submit_button = self.q(css=self._bounded_selector(".action--submit-username"))
        submit_button.first.click()
        self.wait_for_element_visibility(".staff-info__student__report", "Student report is present")

    def expand_staff_grading_section(self):
        """
        Clicks the staff grade control to expand staff grading section for use in staff required workflows.
        """
        self.click_staff_toolbar_button("staff-grading")
        self.q(css=self._bounded_selector(".staff__grade__show-form")).first.click()
        self.wait_for_element_visibility("#staff__assessment__rubric__question--0__0", "staff grading is present")

    @property
    def available_checked_out_numbers(self):
        """
        Gets "N available and M checked out" information from staff grading sections.
        Returns tuple of (N, M)
        """
        if not 'GRADE AVAILABLE RESPONSES' in self.selected_button_names:
            self.expand_staff_grading_section()
        raw_string = self.q(css=self._bounded_selector(".staff__grade__value")).text[0]
        ret = tuple(int(s) for s in raw_string.split() if s.isdigit())
        if len(ret) != 2:
            raise PageConfigurationError("Unable to parse available and checked out numbers")
        return ret

    def verify_available_checked_out_numbers(self, expected_value):
        """
        Waits until the expected value for available and checked out numbers appears. If it does not appear, fails the test.

        expected_value should be a tuple as described in the available_checked_out_numbers property above.
        """
        EmptyPromise(
            lambda: self.available_checked_out_numbers == expected_value,
            "Expected avaiable and checked out values present"
        ).fulfill()

    def submissions_available(self):
        """
        Utility method to check if there are any more learner responses to grade in the staff grading section.
        """
        found = self.q(
            css=self._bounded_selector(".staff__grade__content")
        )
        if found.text[0] == "No other learner responses are available for grading at this time.":
            return False
        return True

    @property
    def learner_report_text(self):
        """
        Returns the text present in the learner report (useful for case where there is no response).
        """
        return self.q(css=self._bounded_selector(".staff-info__student__report")).text[0]

    def verify_learner_report_text(self, expectedText):
        """
        Verifies the learner report text is as expected.
        """
        EmptyPromise(
            lambda: self.learner_report_text == expectedText,
            "Learner report text correct"
        ).fulfill()

    @property
    def learner_report_sections(self):
        """
        Returns the titles of the collapsible learner report sections present on the page.
        """
        self.wait_for_section_titles()
        sections = self.q(css=self._bounded_selector(".ui-staff__subtitle"))
        return [section.text for section in sections]

    def wait_for_section_titles(self):
        """
        Wait for section titles to appear.
        """
        EmptyPromise(
            lambda: len(self.q(css=self._bounded_selector(".ui-staff__subtitle"))) > 0,
            "Section titles appeared"
        ).fulfill()

    def expand_learner_report_sections(self):
        """
        Expands all the sections in the learner report.
        """
        self.wait_for_section_titles()
        self.q(css=self._bounded_selector(".ui-staff__subtitle")).click()

    @property
    def learner_final_score(self):
        """
        Returns the final score displayed in the learner report.
        """
        score = self.q(css=self._bounded_selector(".staff-info__student__grade .ui-toggle-visibility__content"))
        if len(score) == 0:
            return None
        return score.text[0]

    def verify_learner_final_score(self, expected_score):
        """
        Verifies that the final score in the learner report is equal to the expected value.
        """
        EmptyPromise(
            lambda: self.learner_final_score == expected_score,
            "Learner score is updated"
        ).fulfill()

    @property
    def learner_response(self):
        return self.q(
            css=self._bounded_selector(".staff-info__student__response .ui-toggle-visibility__content")
        ).text[0]

    def staff_assess(self, options_selected, continue_after=False):
        for criterion_num, option_num in enumerate(options_selected):
            sel = "#staff__assessment__rubric__question--{criterion_num}__{option_num}".format(
                assessment_type="staff",
                criterion_num=criterion_num,
                option_num=option_num
            )
            self.q(css=self._bounded_selector(sel)).first.click()
        self.submit_assessment(continue_after)

    def submit_assessment(self, continue_after=False):
        """
        Submit a staff assessment of the problem.
        """
        filter_text = "Submit assessment"
        if continue_after:
            filter_text += " and continue grading"
        self.q(css=self._bounded_selector("button.action--submit")).filter(text=filter_text).first.click()

    def cancel_submission(self):
        """
        Cancel a learner's assessment.
        """
        # Must put a comment to enable the submit button.
        self.q(css=self._bounded_selector("textarea.cancel_submission_comments")).fill("comment")
        self.submit(button_css=".action--submit-cancel-submission")

    def status_text(self, section):
        """
        Return the status text (as an array of strings) as shown in the staff area section.

        Args:
            section: the classname of the section for which text should be returned
                (for example, 'peer__assessments', 'submitted__assessments', or 'self__assessment'

        Returns: array of strings representing the text(for example, ['Good', u'5', u'5', u'Excellent', u'3', u'3'])

        """

        table_elements = self.q(
            css=self._bounded_selector(".staff-info__{} .staff-info__status__table .value".format(section))
        )
        text = []
        for value in table_elements:
            text.append(value.text)

        return text
