"""
Gives the time taken by
    find_active_assessments
    get_submission_for_review
    get_submission_for_over_grading
    methods for particular set of workflows.
"""
import random
import datetime

from django.core.management.base import BaseCommand

from openassessment.assessment.models import PeerWorkflow


class Command(BaseCommand):
    """
    Note the time taken by queries.
    """

    help = ("Test the performance for "
            "find_active_assessments, "
            "get_submission_for_review & "
            "get_submission_for_over_grading"
            "methods.")

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        """
        Execute the command.

        Args:
            None
        """
        peer_workflow_count = PeerWorkflow.objects.filter(submission_uuid__isnull=False).count()

        peer_workflow_ids = [random.randint(1, peer_workflow_count) for num in range(100)]
        peer_workflows = list(PeerWorkflow.objects.filter(id__in=peer_workflow_ids))

        pw_dt_before = datetime.datetime.now()

        for peer_workflow in peer_workflows:
            peer_workflow.find_active_assessments()

        pw_dt_after = datetime.datetime.now()
        time_taken = pw_dt_after - pw_dt_before

        print "Time taken by (find_active_assessments) method Is:  %s " % time_taken

        ####  get_submission_for_review ####

        pw_dt_before = datetime.datetime.now()

        for peer_workflow in peer_workflows:
            peer_workflow.get_submission_for_review(2)

        pw_dt_after = datetime.datetime.now()
        time_taken = pw_dt_after - pw_dt_before

        print "Time taken by (get_submission_for_review) method Is:  %s " % time_taken

        ####   get_submission_for_over_grading ####

        pw_dt_before = datetime.datetime.now()

        for peer_workflow in peer_workflows:
            peer_workflow.get_submission_for_over_grading()

        pw_dt_after = datetime.datetime.now()
        time_taken = pw_dt_after - pw_dt_before

        print "Time taken by (get_submission_for_over_grading) method Is:  %s " % time_taken
