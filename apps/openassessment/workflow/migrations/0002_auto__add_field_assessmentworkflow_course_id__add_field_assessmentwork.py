# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AssessmentWorkflow.course_id'
        db.add_column('workflow_assessmentworkflow', 'course_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, db_index=True),
                      keep_default=False)

        # Adding field 'AssessmentWorkflow.item_id'
        db.add_column('workflow_assessmentworkflow', 'item_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, db_index=True),
                      keep_default=False)

        # Create a composite index of course_id, item_id, and status
        db.create_index('workflow_assessmentworkflow', ['course_id', 'item_id', 'status'])


    def backwards(self, orm):
        # Delete the composite index of course_id, item_id, and status
        db.delete_index('workflow_assessmentworkflow', ['course_id', 'item_id', 'status'])

        # Deleting field 'AssessmentWorkflow.course_id'
        db.delete_column('workflow_assessmentworkflow', 'course_id')

        # Deleting field 'AssessmentWorkflow.item_id'
        db.delete_column('workflow_assessmentworkflow', 'item_id')


    models = {
        'workflow.assessmentworkflow': {
            'Meta': {'ordering': "['-created']", 'object_name': 'AssessmentWorkflow'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'peer'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'status_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'status'"}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '36', 'blank': 'True'})
        }
    }

    complete_apps = ['workflow']
