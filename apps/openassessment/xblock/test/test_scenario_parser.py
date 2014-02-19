"""Tests the Workbench Scenario Parser functionality."""

from lxml import etree

from django.test import TestCase

from openassessment.xblock.scenario_parser import ScenarioParser


class TestScenarioParser(TestCase):
    """Test the ScenarioParser XML parsing class, which turns xml into filled XBlocks.

    This does the simplest possible set of tests, just calling the parser utility 
    methods and confirming that their return results are correct, have good types, etc."""

    def setUp(self):
        self.test_parser = ScenarioParser("Dummy XBlock", "Dummy XML")

    def test_get_prompt(self):
        """Given a <prompt> node, return its text."""
        prompt_text = "5de0ef7cc2c7469383b58febd2fdac29"
        prompt_xml = etree.fromstring("<prompt>{words}</prompt>".format(words=prompt_text))
        self.assertEqual(self.test_parser.get_prompt(prompt_xml), prompt_text)

    def test_get_rubric(self):
        """Given a <rubric> tree, return a instructions and a list of criteria"""
        rubric_instructions_text = "This text is general instructions relating to this rubric. There should only be one set of instructions for the rubric."
        criterion_instructions_text = "This text is instructions for this criterion. There can be multiple criteria, but each one should only have one set of instructions."
        criterion_option_explain_text = "And this explains what the label for this option means. There can be only one explanation per label."
        rubric_text = """<rubric>
             {rit}
             <criterion name="myCrit">
               {cit}
               <option val="99">
                 This is some text labeling the criterion option worth 99 points
                 Three can be multiple options per criterion.
                 <explain>
                   {coet}
                 </explain>
               </option>
             </criterion>
           </rubric>""".format(rit=rubric_instructions_text,
                               cit=criterion_instructions_text,
                               coet=criterion_option_explain_text)
        rubric_xml = etree.fromstring(rubric_text)
        rubric_instructions, rubric_criteria = self.test_parser.get_rubric(rubric_xml)

        # Basic shape of the rubric: instructions and criteria
        self.assertEqual(rubric_instructions, rubric_instructions_text)
        self.assertEqual(len(rubric_criteria), 1)

        # Look inside the criterion to make sure it's shaped correctly
        criterion = rubric_criteria[0]
        self.assertEqual(criterion['name'], 'myCrit')
        self.assertEqual(criterion['instructions'], criterion_instructions_text)
        self.assertEqual(criterion['total_value'], 99)
        self.assertEqual(len(criterion['options']), 1)

        # And within the criterion, check that options appear to come out well-formed
        criterion_option_value, criterion_option, criterion_explanation = criterion['options'][0]
        self.assertEqual(int(criterion_option_value), 99)
        self.assertEqual(criterion_explanation, criterion_option_explain_text)

    def test_get_assessments(self):
        """Given an <assessments> list, return a list of assessment modules."""
        assessments = """<assessments>
                <self-assessment name='0382e03c808e4f2bb12dfdd2d45d5c4b'
                       must_grade="999"
                       must_be_graded_by="73" />
                <peer-assessment start="2014-12-20T19:00-7:00"
                          due="2014-12-21T22:22-7:00"
                          must_grade="5"
                          must_be_graded_by="3" />
                <self-assessment />
                </assessments>"""
        assessments_xml = etree.fromstring(assessments)
        parsed_list = self.test_parser.get_assessments(assessments_xml)

        # Self assessments take all the parameters, but mostly ignore them.
        self.assertEqual(parsed_list[0].assessment_type, 'self-assessment')
        self.assertEqual(parsed_list[0].name, '0382e03c808e4f2bb12dfdd2d45d5c4b')
        self.assertEqual(parsed_list[0].must_grade, 1)
        self.assertEqual(parsed_list[0].must_be_graded_by, 0)

        # Peer assessments are more interesting
        self.assertEqual(parsed_list[1].assessment_type, 'peer-assessment')
        self.assertEqual(parsed_list[1].name, '')
        self.assertEqual(parsed_list[1].must_grade, 5)
        self.assertEqual(parsed_list[1].must_be_graded_by, 3)

        # We can parse arbitrary workflow descriptions as a list of assessments.
        # Whether or not the workflow system can use them is another matter
        self.assertEqual(parsed_list[2].assessment_type, 'self-assessment')

