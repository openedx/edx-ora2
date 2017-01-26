"""
Celery looks for tasks in this module,
so import the tasks we want the workers to implement.
"""
# pylint:disable=W0611
from .worker.training import train_classifiers, reschedule_training_tasks
from .worker.grading import grade_essay, reschedule_grading_tasks
