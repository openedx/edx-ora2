# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am an author')
def given_i_am_an_author(step):
    pass

@step(u'And: I configure "([^"]*)" required reviewers per student')
def and_i_configure_required_reviewers_per_student(step, required):
    pass

@step(u'And: I configure "([^"]*)" required reviewers per submission')
def and_i_configure_required_reviewers_per_student(step, required):
    pass

@step(u'Then: The validation "([^"]*)"')
def then_the_validation(step, result):
    pass
