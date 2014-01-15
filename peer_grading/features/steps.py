# -*- coding: utf-8 -*-
from lettuce import step

@step(u'Given: I have defined a step')
def given_i_have_defined_a_step(step):
    pass

@step(u'And: I have implemented the step in lettuce')
def and_i_have_implemented_the_step_in_lettuce(step):
    pass

@step(u'Then: The spec should run in Travis')
def then_the_spec_should_run_in_travis(step):
    pass
