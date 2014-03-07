from xblock.core import XBlock
from openassessment.workflow import api as workflow_api

class WorkflowMixin(object):

    @XBlock.json_handler
    def handle_workflow_info(self, data, suffix=''):
        if not self.submission_uuid:
            return None
        return workflow_api.get_workflow_for_submission(
            self.submission_uuid, self.workflow_requirements()
        )

    def workflow_requirements(self):
        assessment_ui_model = self.get_assessment_module('peer-assessment')
        return {
            "peer": {
                "must_grade": assessment_ui_model["must_grade"],
                "must_be_graded_by": assessment_ui_model["must_be_graded_by"]
            }
        }

    def get_workflow_info(self):
        if not self.submission_uuid:
            return {}
        return workflow_api.get_workflow_for_submission(
            self.submission_uuid, self.workflow_requirements()
        )
