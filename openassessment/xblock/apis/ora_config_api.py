""" External API for ORA Configuration data """

from openassessment.xblock.utils.user_data import get_user_preferences


class ORAConfigAPI:
    # xblock fields
    XBLOCK_FIELDS = [
        "allow_file_upload",
        "allow_latex",
        "allow_multiple_files",
        "date_config_type",
        "file_upload_response_raw",
        "file_upload_type_raw",
        "has_saved",
        "leaderboard_show",
        "prompt",
        "prompts_type",
        "rubric_criteria",
        "rubric_feedback_prompt",
        "rubric_feedback_default_text",
        "rubric_assessments",
        "saved_files_descriptions",
        "saved_files_names",
        "saved_files_sizes",
        "saved_response",
        "selected_teamset_id",
        "show_rubric_during_response",
        "submission_due",
        "submission_start",
        "submission_uuid",
        "teams_enabled",
        "text_response_raw",
        "text_response_editor",
        "title",
        "white_listed_file_types_string",
    ]
    CONFIG_FIELDS = [
        "file_upload_type",
        "file_upload_response",
        "group_access",
        "prompts",
        "text_response",
    ]
    ORA_FIELDS = [
        "assessment_steps",
        "course",
        "is_admin",
        "is_course_staff",
        "is_beta_tester",
        "in_studio_preview",
        "has_real_user",
        "rubric_criteria_with_labels",
        "valid_assessments",
    ]

    def __init__(self, block):
        self._block = block

        for field in self.XBLOCK_FIELDS + self.CONFIG_FIELDS + self.ORA_FIELDS:
            setattr(self, field, getattr(block, field))

    def translate(self, string):
        """Wrapper for ugettext"""
        return self._block._(string)

    def publish_event(self, function_name, data):
        self._block.runtime.publish(self._block, function_name, data)

    @property
    def course_id(self):
        return self._block.course_id

    # NOTE - Do we need this? Is this the same as block ID?
    @property
    def location(self):
        return self._block.location

    @property
    def base_asset_url(self):
        course_key = self._block.location.course_key if hasattr(self._block, "location") else None
        return self._block.get_base_url_path_for_course_assets(course_key)  # pylint-ignore

    @property
    def student_item_dict(self):
        return self.get_student_item_dict()

    @property
    def anonymous_user_id_from_xmodule_runtime(self):
        return self.anonymous_user_id_from_xmodule_runtime()

    # Team Properties
    @property
    def has_team(self):
        return self._block.has_team

    @property
    def is_team_assignment(self):
        return self._block.is_team_assignment

    @property
    def team(self):
        return self._block.team

    @property
    def teamset_config(self):
        return self._block.teamset_config

    @property
    def teams_configuration_service(self):
        return self._block.teams_configuration_service

    @property
    def teams_service(self):
        return self._block.teams_service

    @property
    def user_service(self):
        return self._block.runtime.service(self._block, "user")

    @property
    def user_state_service(self):
        return self._block.runtime.service(self._block, "user_state")

    @property
    def valid_access_to_team_assessment(self):
        return self._block.valid_access_to_team_assessment

    @property
    def runtime(self):
        return self._block.runtime

    # Block methods
    def is_user_state_service_available(self):
        return self._block.is_user_state_service_available()

    def get_anonymous_user_id_from_xmodule_runtime(self):
        return self._block.get_anonymous_user_id_from_xmodule_runtime()

    def get_team_for_anonymous_user(self, anonymous_user_id):
        return self._block.get_team_for_anonymous_user(anonymous_user_id)

    def get_anonymous_user_ids_for_team(self):
        return self._block.get_anonymous_user_ids_for_team()

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
        return self._block.get_username(anonymous_user_id)

    def add_team_submission_context(
        self,
        context,
        team_submission_uuid=None,
        individual_submission_uuid=None,
        transform_usernames=False,
    ):
        self._block.add_submission_context(
            context,
            team_submission_uuid,
            individual_submission_uuid,
            transform_usernames,
        )

    def get_team_submission_uuid_from_individual_submission_uuid(self, individual_submission_uuid):
        return self._block.get_tam_submission_uuid_from_individual_submission_uuid(individual_submission_uuid)

    def does_team_have_submission(self, team_id):
        return self._block.does_team_have_submission(team_id)

    def get_team_info(self):
        return self._block.get_team_info()

    def get_student_item_dict(self, anonymous_user_id=None):
        return self._block.get_student_item_dict(anonymous_user_id)

    def get_xblock_id(self):
        return self._block.get_xblock_id()

    def get_real_user(self, anonymous_user_id):
        return self._block.get_real_user(anonymous_user_id)

    def render_assessment(self, path, context_dict):
        return self._block.render_assessment(path, context_dict)

    def render_error(self, error_msg):
        return self._block.render_error(error_msg)

    @property
    def user_preferences(self):
        return get_user_preferences(self.user_service)
