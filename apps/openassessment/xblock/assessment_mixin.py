from django.template import Context
from django.template.loader import get_template
from webob import Response


class AssessmentMixin(object):

    def render(self, path):
        """Render an Assessment Module's HTML

        Given the name of an assessment module, find it in the list of
        configured modules, and ask for its rendered HTML.

        """
        context_dict = {
            "xblock_trace": self._get_xblock_trace(),
            "rubric_instructions": self.rubric_instructions,
            "rubric_criteria": self.rubric_criteria,
        }
        template = get_template(path)
        context = Context(context_dict)
        return Response(template.render(context), content_type='application/html', charset='UTF-8')

    def _get_assessment_module(self, mixin_name):
        """Get a configured assessment module by name.
        """
        for assessment in self.rubric_assessments:
            if assessment.name == mixin_name:
                return assessment