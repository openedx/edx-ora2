# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I am an author')
def given_i_am_an_author(step):
    pass

@step(u'And: I configure a start date in the "([^"]*)"')
def and_i_configure_a_start_date(step, start_date):
    pass

@step(u'And: I configure an end date in the "([^"]*)"')
def and_i_configure_an_end_date(step, end_date):
    pass

@step(u'When: I attempt to review a peer submission')
def when_i_attempt_to_submit_a_submission(step):
    pass

@step(u'Then: My attempt to review a peer submission "([^"]*)"')
def then_my_attempt_to_submit_a_submission(step, result):
    pass
