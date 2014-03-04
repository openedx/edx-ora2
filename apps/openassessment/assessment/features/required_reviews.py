# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am an author')
def given_i_am_an_author(step):
    pass

@step(u'And: I configure "([^"]*)" required reviews per student')
def and_i_configure_required_reviews_per_student(step, required):
    pass

@step(u'And: A student submits a submission')
def and_a_student_submits_a_submission(step):
    pass

@step(u'And: A student reviews "([^"]*)" peer submissions')
def and_a_student_reviews_peer_submissions(step, required):
    pass

@step(u'When: Enough students review the submission')
def when_enough_students_review_the_submission(step):
    pass

@step(u'And: The student requests a grade')
def and_the_student_requests_a_grade(step):
    pass

@step(u'Then: The student is notified they did not review enough peer submissions')
def then_the_student_is_notified_they_did_not_review_enough_peer_submissions(step):
    pass

@step(u'Then: The student receives reviews.')
def then_the_student_receives_reviews(step):
    pass
