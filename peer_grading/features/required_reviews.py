# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am an author')
def given_i_am_an_author(step):
    pass

@step(u'And: I configure "([^"]*)" required reviews per student')
def and_i_configure_required_reviews_per_student(step):
    pass

@step(u'And: A student submits a submission')
def and_a_student_submits_a_submission(step):
    pass

@step(u'And: A student reviews "([^"]*)" peer submissions')
def and_a_student_reviews_peer_submissions(step):
    pass

@step(u'When: "([^"]*)" students review the submission')
def when_students_review_the_submission(step):
    pass

@step(u'Then: The student receives reviews.')
def then_the_student_receives_reviews(step):
    pass