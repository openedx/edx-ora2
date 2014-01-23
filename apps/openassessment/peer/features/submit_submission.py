# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am a student')
def given_i_am_a_student(step):
    pass

@step(u'When: I submit a submission for peer review')
def when_i_submit_a_submission_for_peer_review(step):
    pass

@step(u'Then: I am notified that my submission has been submitted')
def then_i_am_notified_that_my_submission_has_been_submitted(step):
    pass

@step(u'When: I submit a submission for peer review with unicode characters')
def when_i_submit_a_submission_for_peer_review_with_unicode_characters(step):
    pass

@step(u'Then: My submission is submitted and the unicode characters are preserved')
def then_my_submission_is_submitted_and_the_unicode_characters_are_preserved(step):
    pass