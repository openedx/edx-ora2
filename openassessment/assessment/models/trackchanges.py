"""
TrackChanges models used as part of the (optional) "Track Changes" feature,
which allows basic collaborative editing of student submissions.

NOTE: If you make any edits to this file, you can generate migrations using:
    ./manage.py makemigrations openassessment.assessment
"""
import logging
from uuid import uuid4

from django.db import models

logger = logging.getLogger(__name__)


class TrackChanges(models.Model):
    """
    Store copies of student submission texts with inline editing marks
    """
    # A (owner_submission_uuid, scorer_id) pair uniquely specifies a piece of edited content
    owner_submission_uuid = models.UUIDField(db_index=True, default=uuid4)
    scorer_id = models.CharField(max_length=40, db_index=True)
    # edited content allowing multiple prompts (JSON-serialized)
    json_edited_content = models.TextField(blank=True)

    class Meta:
        app_label = 'assessment'
        unique_together = ('owner_submission_uuid', 'scorer_id')

    def as_dict(self):
        return {
            'owner_submission_uuid': self.owner_submission_uuid,
            'scorer_id': self.scorer_id,
            'json_edited_content': self.json_edited_content,
            'id': self.id,
        }

    def __str__(self):
        return str(self.as_dict())
