"""
TrackChanges models used as part of the (optional) "Track Changes" feature,
which allows basic collaborative editing of student submissions.

NOTE: If you make any edits to this file, you can generate migrations using:
    ./manage.py schemamigration openassessment.assessment --auto
"""
import logging

from django.db import models
from django_extensions.db.fields import UUIDField

logger = logging.getLogger(__name__)


class TrackChanges(models.Model):
    """Store copies of student submission texts with inline editing marks."""
    # A (owner_submission_uuid, scorer_id) pair uniquely specifies a piece of edited content
    owner_submission_uuid = UUIDField(version=1, db_index=True)
    scorer_id = models.CharField(max_length=40, db_index=True)
    edited_content = models.TextField(blank=True)

    class Meta:
        app_label = "assessment"

    def as_dict(self):
        return {
            "owner_submission_uuid": self.owner_submission_uuid,
            "scorer_id": self.scorer_id,
            "edited_content": self.edited_content,
            "id": self.id,
        }

    def __str__(self):
        return str(self.as_dict())
