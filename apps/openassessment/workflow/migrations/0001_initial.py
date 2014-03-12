# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AssessmentWorkflow'
        db.create_table('workflow_assessmentworkflow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('status', self.gf('model_utils.fields.StatusField')(default='peer', max_length=100, no_check_for_status=True)),
            ('status_changed', self.gf('model_utils.fields.MonitorField')(default=datetime.datetime.now, monitor=u'status')),
            ('submission_uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=36, db_index=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(db_index=True, unique=True, max_length=36, blank=True)),
        ))
        db.send_create_signal('workflow', ['AssessmentWorkflow'])


    def backwards(self, orm):
        # Deleting model 'AssessmentWorkflow'
        db.delete_table('workflow_assessmentworkflow')


    models = {
        'workflow.assessmentworkflow': {
            'Meta': {'ordering': "['-created']", 'object_name': 'AssessmentWorkflow'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'peer'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'status_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'status'"}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '36', 'blank': 'True'})
        }
    }

    complete_apps = ['workflow']