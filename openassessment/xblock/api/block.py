from openassessment.xblock.api.team import TeamMixinAPI
from openassessment.xblock.api.workflow import WorkflowAPI

class BlockAPI:
    def __init__(self, block):
        self._block = block
        self.team = TeamMixinAPI(block)
        self.workflow = WorkflowAPI(block)

    @property
    def course_id(self):
        return self._block.course_id

    @course_id.setter
    def course_id(self, value):
        self._block.course_id = value

    @property
    def course(self):
        return self._block.course

    @property
    def text_response(self):
        return self._block.text_response

    @text_response.setter
    def text_response(self, value):
        self._block.text_response = value

    @property
    def file_upload_response(self):
        return self._block.file_upload_response

    @file_upload_response.setter
    def file_upload_response(self, value):
        self._block.file_upload_response = value

    @property
    def file_upload_type(self):
        return self._block.file_upload_type

    @file_upload_type.setter
    def file_upload_type(self, value):
        self._block.file_upload_type = value

    @property
    def white_listed_file_types_string(self):
        return self._block.white_listed_file_types_string

    @white_listed_file_types_string.setter
    def white_listed_file_types_string(self, value):
        self._block.white_listed_file_types_string = value

    @property
    def is_user_state_service_available(self):
        return self._block.is_user_state_service_available()

    def get_anonymous_user_id(self, username, course_id):
        return self._block.get_anonymous_user_id(self, username, course_id)

    def get_user_state(self, username):
        return self._block.get_user_state(username)

    def should_use_user_state(self, upload_urls):
        return self._block.should_use_user_state(upload_urls)

    def should_get_all_files_urls(self, upload_urls):
        return self._block.should_get_all_files_urls(upload_urls)

    def get_student_item_dict_from_username_or_email(self, username_or_email):
        return self._block.get_student_item_dict_from_username_or_email(username_or_email)

    @property
    def get_anonymous_user_id_from_xmodule_runtime(self):
        return self._block.get_anonymous_user_id_from_xmodule_runtime()

    @property
    def student_item_dict(self):
        return self.get_student_item_dict()

    def get_student_item_dict(self, anonymous_user_id=None):
        return self._block.get_student_item_dict(anonymous_user_id)

    @property
    def is_admin(self):
        return self._block.is_admin

    @property
    def is_course_staff(self):
        return self._block.is_course_staff

    @property
    def is_beta_tester(self):
        return self._block.is_beta_tester

    @property
    def in_studio_preview(self):
        return self._block.in_studio_preview

    @property
    def has_real_user(self):
        return self._block.has_real_user

    @property
    def prompts(self):
        return self._block.prompts

    @property
    def prompt(self):
        return self._block.prompts

    @prompts.setter
    def prompts(self, value):
        self._block.prompts = value

    @property
    def valid_assessments(self):
        return self._block.valid_assessments

    @property
    def assessment_steps(self):
        return self._block.assessment_steps

    def is_closed(self, step=None, course_staff=None):
        return self._block.is_closed(step, course_staff)

    def get_waiting_details(self, status_details):
        return self._block.get_waiting_details(status_details)

    def is_released(self, step=None):
        return self._block.is_released(step)

    def get_assessment_module(self, mixin_name):
        return self._block.get_assessment_module(mixin_name)

    def publish_assessment_event(self, event_name, assessment, **kwargs):
        self._block.publish_assessment_event(event_name, assessment, **kwargs)

    def get_username(self, anonymous_user_id):
        return self._block(anonymous_user_id)

    @property
    def xblock_id(self):
        return self._block.xblock_id

    @property
    def rubric_criteria(self):
        return self._block.rubric_criteria

    @property
    def rubric_criteria_with_labels(self):
        return self._block.rubric_criteria_with_labels
