import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from base import *
from locust import HttpLocust, TaskSet, task

class MakeManySubmissionsTasks(TaskSet):
    """
    In order to test my migration's performance, I need some submissions in the table.
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=W0613
        """
        Initialize the task set.
        """
        super(MakeManySubmissionsTasks, self).__init__(*args, **kwargs)
        self.hostname = self.locust.host
        self.page = None

    @task
    def generate_data(self):
        """
        Puts some submissions in the database
        """
        self.page = OpenAssessmentPage(self.hostname, self.client, 'peer_then_self')  # pylint: disable=E1101
        self.page.log_in()

        # Submit something
        self.page.submit_response()

class MakeSubDataLocust(HttpLocust):
    """
    Performance test definition
    """
    task_set = MakeManySubmissionsTasks
    min_wait = 0
    max_wait = 100
