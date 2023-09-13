"""
Batch update ORA workflows
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from openassessment import workflow_batch_update_api as tasks

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Refresh/update ORA workflows for all submissions
    """

    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        parser.add_argument(
            '--course_id',
            dest='course_id',
            help='Optional course id',
        )

        parser.add_argument(
            '--item_id',
            dest='item_id',
            help='Optional ORA block id',
        )

    def handle(self, *args, **options):

        if options.get("course_id") and options.get("item_id"):
            raise CommandError("Only single scope limiting optional argument can be specified")

        task_args = []
        if options.get("course_id"):
            task_name = tasks.update_workflows_for_course_task.name
            task_args = [options.get("course_id")]
            result = tasks.update_workflows_for_course_task.apply_async(task_args)
        elif options.get("item_id"):
            task_name = tasks.update_workflows_for_ora_block_task.name
            task_args = [options.get("item_id")]
            result = tasks.update_workflows_for_ora_block_task.apply_async(task_args)
        else:
            task_name = tasks.update_workflows_for_all_blocked_submissions_task.name
            result = tasks.update_workflows_for_all_blocked_submissions_task.apply_async()

        log.info("Created %s[%s] with arguments %s",
                 task_name,
                 result.task_id,
                 task_args
                 )
