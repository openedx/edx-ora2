# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Rubric'
        db.create_table('assessment_rubric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, db_index=True)),
        ))
        db.send_create_signal('assessment', ['Rubric'])

        # Adding model 'Criterion'
        db.create_table('assessment_criterion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rubric', self.gf('django.db.models.fields.related.ForeignKey')(related_name='criteria', to=orm['assessment.Rubric'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order_num', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('prompt', self.gf('django.db.models.fields.TextField')(max_length=10000)),
        ))
        db.send_create_signal('assessment', ['Criterion'])

        # Adding model 'CriterionOption'
        db.create_table('assessment_criterionoption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('criterion', self.gf('django.db.models.fields.related.ForeignKey')(related_name='options', to=orm['assessment.Criterion'])),
            ('order_num', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('points', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('explanation', self.gf('django.db.models.fields.TextField')(max_length=10000, blank=True)),
        ))
        db.send_create_signal('assessment', ['CriterionOption'])

        # Adding model 'Assessment'
        db.create_table('assessment_assessment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submissions.Submission'])),
            ('rubric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assessment.Rubric'])),
            ('scored_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('scorer_id', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('score_type', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('feedback', self.gf('django.db.models.fields.TextField')(default='', max_length=10000, blank=True)),
        ))
        db.send_create_signal('assessment', ['Assessment'])

        # Adding model 'AssessmentPart'
        db.create_table('assessment_assessmentpart', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('assessment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='parts', to=orm['assessment.Assessment'])),
            ('option', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assessment.CriterionOption'])),
        ))
        db.send_create_signal('assessment', ['AssessmentPart'])

        # Adding model 'PeerWorkflow'
        db.create_table('assessment_peerworkflow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('item_id', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('submission_uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128, db_index=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
        ))
        db.send_create_signal('assessment', ['PeerWorkflow'])

        # Adding model 'PeerWorkflowItem'
        db.create_table('assessment_peerworkflowitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scorer_id', self.gf('django.db.models.fields.related.ForeignKey')(related_name='items', to=orm['assessment.PeerWorkflow'])),
            ('submission_uuid', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('started_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('assessment', self.gf('django.db.models.fields.IntegerField')(default=-1)),
        ))
        db.send_create_signal('assessment', ['PeerWorkflowItem'])


    def backwards(self, orm):
        # Deleting model 'Rubric'
        db.delete_table('assessment_rubric')

        # Deleting model 'Criterion'
        db.delete_table('assessment_criterion')

        # Deleting model 'CriterionOption'
        db.delete_table('assessment_criterionoption')

        # Deleting model 'Assessment'
        db.delete_table('assessment_assessment')

        # Deleting model 'AssessmentPart'
        db.delete_table('assessment_assessmentpart')

        # Deleting model 'PeerWorkflow'
        db.delete_table('assessment_peerworkflow')

        # Deleting model 'PeerWorkflowItem'
        db.delete_table('assessment_peerworkflowitem')


    models = {
        'assessment.assessment': {
            'Meta': {'ordering': "['-scored_at', '-id']", 'object_name': 'Assessment'},
            'feedback': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '10000', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rubric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assessment.Rubric']"}),
            'score_type': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'scored_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'scorer_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submissions.Submission']"})
        },
        'assessment.assessmentpart': {
            'Meta': {'object_name': 'AssessmentPart'},
            'assessment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parts'", 'to': "orm['assessment.Assessment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assessment.CriterionOption']"})
        },
        'assessment.criterion': {
            'Meta': {'ordering': "['rubric', 'order_num']", 'object_name': 'Criterion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order_num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'prompt': ('django.db.models.fields.TextField', [], {'max_length': '10000'}),
            'rubric': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'criteria'", 'to': "orm['assessment.Rubric']"})
        },
        'assessment.criterionoption': {
            'Meta': {'ordering': "['criterion', 'order_num']", 'object_name': 'CriterionOption'},
            'criterion': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'options'", 'to': "orm['assessment.Criterion']"}),
            'explanation': ('django.db.models.fields.TextField', [], {'max_length': '10000', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order_num': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'points': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'assessment.peerworkflow': {
            'Meta': {'ordering': "['created_at', 'id']", 'object_name': 'PeerWorkflow'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'db_index': 'True'})
        },
        'assessment.peerworkflowitem': {
            'Meta': {'ordering': "['started_at', 'id']", 'object_name': 'PeerWorkflowItem'},
            'assessment': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scorer_id': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['assessment.PeerWorkflow']"}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
        'assessment.rubric': {
            'Meta': {'object_name': 'Rubric'},
            'content_hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'submissions.studentitem': {
            'Meta': {'unique_together': "(('course_id', 'student_id', 'item_id'),)", 'object_name': 'StudentItem'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        },
        'submissions.submission': {
            'Meta': {'ordering': "['-submitted_at', '-id']", 'object_name': 'Submission'},
            'answer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'attempt_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'student_item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submissions.StudentItem']"}),
            'submitted_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '36', 'blank': 'True'})
        }
    }

    complete_apps = ['assessment']