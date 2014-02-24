# -*- coding: utf-8 -*-
"""XBlock scenario parsing routines"""
from openassessment.xblock.ui_models import PeerAssessmentUIModel, SelfAssessmentUIModel, SubmissionUIModel


class ScenarioParser(object):
    """Utility class to capture parsing of xml from runtime scenarios."""

    def __init__(self, xblock, node, unknown_handler=lambda x,y: (x,y)):
        """Save the little bit of state we expect to re-use.
        
        Args:
            xblock (XBlock): The xblock instance whose fields we fill out.
            node (lxml.etree): The root of the xml hierarchy we are to walk.
            unknown_handler (function): A closure over some environmental data
                from our caller, which is used when we encounter an unexpected
                child node.
        """
        self.xblock = xblock
        self.root = node
        self.unknown_handler = unknown_handler

    def get_prompt(self, e):
        """<prompt>This tells you what you should write about. There should be only one prompt.</prompt>"""
        return e.text.strip()

    def get_title(self, e):
        """<title>The title of this block</title>
        """
        return e.text.strip()

    def get_rubric(self, e):
        """<rubric>
             This text is general instructions relating to this rubric.
             There should only be one set of instructions for the rubric.
             <criterion name="myCrit">
               This text is instructions for this criterion. There can be multiple criteria,
               but each one should only have one set of instructions.
               <option val=99>
                 This is some text labeling the criterion option worth 99 points
                 Three can be multiple options per criterion.
                 <explain>
                   And this explains what the label for this option means. There can be only
                   one explanation per label.
                 </explain
               </option>
             </criterion>
           </rubric>"""
        rubric_criteria = []
        for criterion in e:
            crit = {
                'name': criterion.attrib.get('name', ''),
                'prompt': criterion.text.strip(),
                'options': [],
            }
            for option in criterion:
                explanations = option.getchildren()
                if explanations and len(explanations) == 1 and explanations[0].tag == 'explain':
                    explanation = explanations[0].text.strip()
                else: 
                    explanation = ''

                crit['options'].append(
                    {
                        'name': option.text.strip(),
                        'points': int(option.attrib['val']),
                        'explanation': explanation,
                    }
                )
            rubric_criteria.append(crit)

        return (e.text.strip(), rubric_criteria)

    def get_assessments(self, assessments):
        """<assessments>
            <!-- There can be multiple types of assessments given in any
                 arbitrary order, like this self assessment followed by a
                 peer assessment -->
            <self-assessment />
            <peer-assessment start="2014-12-20T19:00-7:00"
                      due="2014-12-21T22:22-7:00"
                      must_grade="5"
                      must_be_graded_by="3" />
           </peer-assessment>"""
        assessment_list = [SubmissionUIModel()]
        for asmnt in assessments:
            assessment = None
            assessment_type = asmnt.tag
            if 'peer-assessment' == assessment_type:
                assessment = PeerAssessmentUIModel()
                assessment.must_grade = int(asmnt.attrib.get('must_grade', 1))
                assessment.must_be_graded_by = int(asmnt.attrib.get('must_be_graded_by', 0))
            elif 'self-assessment' == assessment_type:
                assessment = SelfAssessmentUIModel()

            if assessment:
                assessment.name = asmnt.attrib.get('name', '')
                assessment.start_datetime = asmnt.attrib.get('start', None)
                assessment.due_datetime = asmnt.attrib.get('due', None)
                assessment_list.append(assessment)

        return assessment_list

    def parse(self):
        """Instantiate xblock object from runtime XML definition."""

        self.xblock.start_datetime = self.root.attrib.get('start', None)
        self.xblock.due_datetime = self.root.attrib.get('due', None)

        for child in self.root:
            if child.tag == 'prompt':
                self.xblock.prompt = self.get_prompt(child)
            elif child.tag == 'rubric':
                (self.xblock.rubric_instructions, 
                 self.xblock.rubric_criteria) = self.get_rubric(child)
            elif child.tag == 'title':
                self.xblock.title = self.get_title(child)
            elif child.tag == 'assessments':
                self.xblock.rubric_assessments = self.get_assessments(child)
            else:
                self.unknown_handler(self.xblock, child)
        return self.xblock
