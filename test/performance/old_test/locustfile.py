import ../base.py
from locust import HttpLocust, TaskSet, task

class PeerSelfAndExampleBasedTasks(TaskSet):
    """
    Virtual user interactions with the OpenAssessment XBlock.
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=W0613
        """
        Initialize the task set.
        """
        super(PeerSelfAndExampleBasedTasks, self).__init__(*args, **kwargs)
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
    task_set = PeerSelfAndExampleBasedTasks
    min_wait = 10000
    max_wait = 15000
