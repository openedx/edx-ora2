# -*- coding: utf-8 -*-
"""
Tests for grade handlers in Open Assessment XBlock.
"""
import copy
import json
from submissions import api as submission_api
from openassessment.peer import api as peer_api
from .base import XBlockHandlerTestCase, scenario


class TestGrade(XBlockHandlerTestCase):

    ASSESSMENTS = [
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
        },
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'feedback': u'Good job!',
        },
    ]

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_render_grade(self, xblock):

        # Create a submission from the user
        student_item = xblock.get_student_item_dict()
        submission = submission_api.create_submission(student_item, self.SUBMISSION)

        scorer_submissions = []
        for scorer_name, assessment in zip(['McNulty', 'Freamon'], self.ASSESSMENTS):
            # Create a submission for each scorer
            scorer = copy.deepcopy(student_item)
            scorer['student_id'] = scorer_name
            scorer_sub = submission_api.create_submission(scorer, self.SUBMISSION)

            # Store the scorer's submission so our user can assess it later
            scorer_submissions.append(scorer_sub)

            # Create an assessment of the user's submission
            peer_api.create_assessment(
                submission['uuid'], scorer_name, 2, 2,
                assessment, {'criteria': xblock.rubric_criteria}
            )

        # Have our user make assessments (so she can get a score)
        for submission in scorer_submissions:
            peer_api.create_assessment(
                submission['uuid'], 'Greggs', 2, 2,
                self.ASSESSMENTS[0], {'criteria': xblock.rubric_criteria}
            )

        # Render the view
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that feedback from each scorer appears in the view
        self.assertIn(u'єאςєɭɭєภՇ ฬ๏гк!', resp.decode('utf-8'))
        self.assertIn(u'Good job!', resp.decode('utf-8'))
