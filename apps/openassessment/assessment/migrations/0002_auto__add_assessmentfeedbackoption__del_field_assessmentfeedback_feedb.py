# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AssessmentFeedbackOption'
        db.create_table('assessment_assessmentfeedbackoption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('assessment', ['AssessmentFeedbackOption'])

        # Deleting field 'AssessmentFeedback.feedback'
        db.delete_column('assessment_assessmentfeedback', 'feedback')

        # Deleting field 'AssessmentFeedback.helpfulness'
        db.delete_column('assessment_assessmentfeedback', 'helpfulness')

        # Adding field 'AssessmentFeedback.feedback_text'
        db.add_column('assessment_assessmentfeedback', 'feedback_text',
                      self.gf('django.db.models.fields.TextField')(default='', max_length=10000),
                      keep_default=False)

        # Adding M2M table for field options on 'AssessmentFeedback'
        db.create_table('assessment_assessmentfeedback_options', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('assessmentfeedback', models.ForeignKey(orm['assessment.assessmentfeedback'], null=False)),
            ('assessmentfeedbackoption', models.ForeignKey(orm['assessment.assessmentfeedbackoption'], null=False))
        ))
        db.create_unique('assessment_assessmentfeedback_options', ['assessmentfeedback_id', 'assessmentfeedbackoption_id'])


    def backwards(self, orm):
        # Deleting model 'AssessmentFeedbackOption'
        db.delete_table('assessment_assessmentfeedbackoption')

        # Adding field 'AssessmentFeedback.feedback'
        db.add_column('assessment_assessmentfeedback', 'feedback',
                      self.gf('django.db.models.fields.TextField')(default='', max_length=10000),
                      keep_default=False)

        # Adding field 'AssessmentFeedback.helpfulness'
        db.add_column('assessment_assessmentfeedback', 'helpfulness',
                      self.gf('django.db.models.fields.IntegerField')(default=2),
                      keep_default=False)

        # Deleting field 'AssessmentFeedback.feedback_text'
        db.delete_column('assessment_assessmentfeedback', 'feedback_text')

        # Removing M2M table for field options on 'AssessmentFeedback'
        db.delete_table('assessment_assessmentfeedback_options')


    models = {
        'assessment.assessment': {
            'Meta': {'ordering': "['-scored_at', '-id']", 'object_name': 'Assessment'},
            'feedback': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '10000', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rubric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assessment.Rubric']"}),
            'score_type': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'scored_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'scorer_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
        'assessment.assessmentfeedback': {
            'Meta': {'object_name': 'AssessmentFeedback'},
            'assessments': ('django.db.models.fields.related.ManyToManyField', [], {'default': 'None', 'related_name': "'assessment_feedback'", 'symmetrical': 'False', 'to': "orm['assessment.Assessment']"}),
            'feedback_text': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '10000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'default': 'None', 'to': "orm['assessment.AssessmentFeedbackOption']", 'symmetrical': 'False'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'db_index': 'True'})
        },
        'assessment.assessmentfeedbackoption': {
            'Meta': {'object_name': 'AssessmentFeedbackOption'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
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
            'completed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'db_index': 'True'})
        },
        'assessment.peerworkflowitem': {
            'Meta': {'ordering': "['started_at', 'id']", 'object_name': 'PeerWorkflowItem'},
            'assessment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assessment.Assessment']", 'null': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'graded_by'", 'to': "orm['assessment.PeerWorkflow']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'scorer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'graded'", 'to': "orm['assessment.PeerWorkflow']"}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'submission_uuid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
        'assessment.rubric': {
            'Meta': {'object_name': 'Rubric'},
            'content_hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['assessment']