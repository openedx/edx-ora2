# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StudentItem'
        db.create_table('submissions_studentitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('item_id', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('item_type', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('submissions', ['StudentItem'])

        # Adding unique constraint on 'StudentItem', fields ['course_id', 'student_id', 'item_id']
        db.create_unique('submissions_studentitem', ['course_id', 'student_id', 'item_id'])

        # Adding model 'Submission'
        db.create_table('submissions_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=36, blank=True)),
            ('student_item', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submissions.StudentItem'])),
            ('attempt_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('submitted_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('answer', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('submissions', ['Submission'])

        # Adding model 'Score'
        db.create_table('submissions_score', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_item', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submissions.StudentItem'])),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submissions.Submission'], null=True)),
            ('points_earned', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('points_possible', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
        ))
        db.send_create_signal('submissions', ['Score'])


    def backwards(self, orm):
        # Removing unique constraint on 'StudentItem', fields ['course_id', 'student_id', 'item_id']
        db.delete_unique('submissions_studentitem', ['course_id', 'student_id', 'item_id'])

        # Deleting model 'StudentItem'
        db.delete_table('submissions_studentitem')

        # Deleting model 'Submission'
        db.delete_table('submissions_submission')

        # Deleting model 'Score'
        db.delete_table('submissions_score')


    models = {
        'submissions.score': {
            'Meta': {'object_name': 'Score'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points_earned': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'points_possible': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'student_item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submissions.StudentItem']"}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submissions.Submission']", 'null': 'True'})
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

    complete_apps = ['submissions']