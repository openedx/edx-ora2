from django.template import Context
from django.template.loader import get_template
from webob import Response


class AssessmentMixin(object):

    def render(self, path, context_dict=None):
        """Render an Assessment Module's HTML

        Given the name of an assessment module, find it in the list of
        configured modules, and ask for its rendered HTML.

        """
        if not context_dict: context_dict = {}
        context_dict["xblock_trace"] = self.get_xblock_trace()
        context_dict["rubric_instructions"] = self.rubric_instructions
        context_dict["rubric_criteria"] = self.rubric_criteria

        template = get_template(path)
        context = Context(context_dict)
        return Response(template.render(context), content_type='application/html', charset='UTF-8')
