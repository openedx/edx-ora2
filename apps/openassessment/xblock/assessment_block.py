from django.template import Context
from django.template.loader import get_template


class AssessmentBlock(object):
    assessment_type = None
    name = ''
    start_datetime = None
    due_datetime = None
    must_grade = 1
    must_be_graded_by = 0
    navigation_text = ""
    path = ""
    title = ""

    def create_ui_model(self):
        return {
            "assessment_type": self.assessment_type,
            "name": self.name,
            "start_datetime": self.start_datetime,
            "due_datetime": self.due_datetime,
            "must_grade": self.must_grade,
            "must_be_graded_by": self.must_be_graded_by,
            "navigation_text": self.navigation_text,
            "title": self.title
        }

    def render(self, context_dict):
        template = get_template(self.path)
        context = Context(context_dict)
        return template.render(context)