# -*- coding: utf-8 -*-
"""XBlock scenario parsing routines"""

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
            crit = {'name': criterion.attrib.get('name', ''),
                    'instructions': criterion.text.strip(),
                    'total_value': 0,
                    'options': [],
                   }
            for option in criterion:
                explanations = option.getchildren()
                if explanations and len(explanations) == 1 and explanations[0].tag == 'explain':
                    explanation = explanations[0].text.strip()
                else: 
                    explanation = ''
                crit['options'].append((option.attrib['val'], option.text.strip(), explanation))
            crit['total_value'] = max(int(x[0]) for x in crit['options'])
            rubric_criteria.append(crit)
        return (e.text.strip(), rubric_criteria)

    def get_evals(self, evaluations):
        """<evals>
            <!-- There can be multiple types of assessments given in any
                 arbitrary order, like this self assessment followed by a
                 peer assessment -->
            <self />
            <peereval start="2014-12-20T19:00-7:00"
                      due="2014-12-21T22:22-7:00"
                      must_grade="5"
                      must_be_graded_by="3" />
           </evals>"""
        return [{'type': ev.tag,
                  'name': ev.attrib.get('name', ''),
                  'start_datetime': ev.attrib.get('start', None),
                  'due_datetime': ev.attrib.get('due', None),
                  # These attrs are accepted for self, ai evals, but ignored:
                  'must_grade': int(ev.attrib.get('must_grade', 1) if ev.tag == 'peereval' else 1),
                  'must_be_graded_by': int(ev.attrib.get('must_be_graded_by', 0) if ev.tag == 'peereval' else 0), 
                } for ev in evaluations]

    def parse(self):
        """Instantiate xblock object from runtime XML definition."""
        for child in self.root:
            if child.tag == 'prompt':
                self.xblock.prompt = self.get_prompt(child)
            elif child.tag == 'rubric':
                (self.xblock.rubric_instructions, 
                 self.xblock.rubric_criteria) = self.get_rubric(child)
            elif child.tag == 'evals':
                self.xblock.rubric_evals = self.get_evals(child)
            else:
                self.unknown_handler(self.xblock, child)
        return self.xblock

