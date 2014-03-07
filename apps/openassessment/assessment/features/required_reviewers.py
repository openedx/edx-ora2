# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am an author')
def given_i_am_an_author(step):
    pass

@step(u'And: I configure "([^"]*)" required reviewers per submissions')
def and_i_configure_required_reviewers_per_submission(step, required):
    pass

@step(u'And: I submit a submission')
def and_i_submit_a_submission(step):
    pass

@step(u'And: I review enough peer submissions')
def and_i_review_enough_peer_submissions(step):
    pass

@step(u'When: "([^"]*)" students review the submission')
def when_students_review_the_submission(step, required):
    pass

@step(u'Then: I receive my reviews.')
def then_i_receive_my_reviews(step):
    pass