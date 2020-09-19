class OpenAssessmentTemplatesMixin(object):
    """
    This helps to get templates for different type of assessment that is
    offered.
    """

    @classmethod
    def templates(cls):
        """
        Returns a list of dictionary field: value objects that describe possible templates.

        VALID_ASSESSMENT_TYPES needs to be declared as a class variable to use it.
        """
        templates = []
        for assesment_type in cls.VALID_ASSESSMENT_TYPES:
            template_id = assesment_type
            display_name = cls.VALID_ASSESSMENT_TYPES_DISPLAY_NAMES.get(
                assesment_type)
            template = cls._create_template_dict(template_id, display_name)
            templates.append(template)
        return templates

    def _create_template_dict(cls, template_id, display_name):
        """
        Returns a template dictionary which can be used with Studio API
        """
        return {
            "template_id": template_id,
            "metadata": {
                "display_name": display_name,
            }
        }
