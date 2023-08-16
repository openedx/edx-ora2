""" Mixin to encapsulate teams-related behavior """

class TeamMixinAPI:
    """Team Mixin introducing all teams-related functionality."""
    def __init__(self, block):
        self._raw_block = block;

    @property
    def is_team_assignment(self):
        return self._raw_block.is_team_assignment()

    @property
    def teams_service(self):
        return self._raw_block.teams_service()

    @property
    def teams_configuration_service(self):
        return self._raw_block.teams_configuration_service()

    def get_team_for_anonymous_user(self, anonymous_user_id):
        return self._raw_block.get_team_for_anonymous_user(anonymous_user_id)

    @property
    def team(self):
        return self._raw_block.team()

    @property
    def teamset_config(self):
        return self._raw_block.teamset_config()

    @property
    def has_team(self):
        return self._raw_block.has_team()

    @property
    def valid_access_to_team_assessment(self):
        return self._raw_block.valid_access_to_team_assessment

    def add_team_submission_context(
        self, context, team_submission_uuid=None, individual_submission_uuid=None, transform_usernames=False
    ):
        self._raw_block.add_submission_context(
            context, team_submission_uuid, individual_submission_uuid, transform_usernames
        )

    @property
    def get_team_info(self):
        return self._raw_block.get_team_info

    @property
    def get_anonymous_user_ids_for_team(self):
        return self._raw_block.get_anonymous_user_ids_for_team

    def get_team_submission_uuid_from_individual_submission_uuid(self, individual_submission_uuid):
        return self._raw_block.get_tam_submission_uuid_from_individual_submission_uuid(
            individual_submission_uuid
        )

    def does_team_have_submission(self, team_id):
        return self._raw_block.does_team_have_submission(team_id)
