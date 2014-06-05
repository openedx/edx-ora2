# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AssessmentWorkflowStep'
        db.create_table('workflow_assessmentworkflowstep', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='steps', to=orm['workflow.AssessmentWorkflow'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('submitter_completed_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('assessment_completed_at', self.gf('django.db.models.fields.DateTimeField')(default=None, null=True)),
            ('order_num', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('workflow', ['AssessmentWorkflowStep'])


    def backwards(self, orm):
        # Deleting model 'AssessmentWorkflowStep'
        db.delete_table('workflow_assessmentworkflowstep')


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
        },
        'workflow.assessmentworkflowstep': {
            'Meta': {'ordering': "['workflow', 'order_num']", 'object_name': 'AssessmentWorkflowStep'},
            'assessment_completed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'order_num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'submitter_completed_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'steps'", 'to': "orm['workflow.AssessmentWorkflow']"})
        }
    }

    complete_apps = ['workflow']