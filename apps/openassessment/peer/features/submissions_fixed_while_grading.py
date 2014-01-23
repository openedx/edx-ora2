# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am a student')
def given_i_am_a_student(step):
    pass

@step(u'When: I submit a submission for peer review')
def when_i_submit_a_submission_for_peer_review(step):
    pass

@step(u'And: A peer begins to review my submission')
def and_a_peer_begins_to_review_my_submission(step):
    pass

@step(u'Then: I cannot modify my submission')
def then_i_cannot_modify_my_submission(step):
    pass

@step(u'And: I modify my submission')
def and_i_modify_my_submission(step):
    pass

@step(u'Then: I successfully save changes to my submission')
def then_i_successfully_save_changes_to_my_submission(step):
    pass


