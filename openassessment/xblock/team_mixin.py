""" Mixin to encapsulate teams-related behavior """
import logging

from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError
from submissions.team_api import (
    get_team_submission,
    get_team_submission_for_team,
    get_team_submission_from_individual_submission,
    get_team_submission_for_student,
    get_team_submission_student_ids
)
from submissions.errors import TeamSubmissionNotFoundError

from openassessment.xblock.data_conversion import list_to_conversational_format

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TeamMixin:
    """Team Mixin introducing all teams-related functionality."""

    STAFF_OR_PREVIEW_INFO = {
        'team_name': '< TEAM NAME >',
        'team_usernames': ['< USERNAMES >'],
        'team_url': '#TEAM_URL',
        'team_id': 'TEAM_ID',
    }

    def is_team_assignment(self):
        # pylint: disable=no-member
        return self.teams_enabled and self.team_submissions_enabled

    @cached_property
    def teams_service(self):
        try:
            return self.runtime.service(self, 'teams')
        except NoSuchServiceError:
            logger.error('%s: Teams service unavailable', self.location)
            raise

    @cached_property
    def teams_configuration_service(self):
        try:
            return self.runtime.service(self, 'teams_configuration')
        except NoSuchServiceError:
            logger.error('%s: Teams Configuration service unavailable', self.location)
            raise

    def get_team_for_anonymous_user(self, anonymous_user_id):
        """
        For course_id associated with this ORA block, returns the provided user's
        CourseTeam, or None if the user is not a member of a team in this course or
        if the teams service is unavailable.
        Raises:
            - ObjectDoesNotExist if the user associated with `anonymous_user_id`
                                    can not be found
        """
        user = self.get_real_user(anonymous_user_id)
        if not user:
            logger.error('%s: User lookup for anonymous_user_id %s failed', self.location, anonymous_user_id)
            raise ObjectDoesNotExist()
        try:
            team = self.teams_service.get_team(user, self.course_id, self.selected_teamset_id)
        except NoSuchServiceError:
            logger.debug("%s %s [AU-660]", self.location, anonymous_user_id)
            return None
        return team

    @cached_property
    def team(self):
        """
        For the user and course_id associated with this ORA block, returns the user's
        CourseTeam, or None if the user is not a member of a team in this course.
        Raises:
            - ObjectDoesNotExist if the user associated with `anonymous_user_id`
                                    can not be found
        """
        return self.get_team_for_anonymous_user(
            self.get_anonymous_user_id_from_xmodule_runtime()
        )

    @cached_property
    def teamset_config(self):
        course_id = self.location.course_key if hasattr(self, 'location') else None
        teams_config = self.teams_configuration_service.get_teams_configuration(course_id)
        try:
            return teams_config.teamsets_by_id[self.selected_teamset_id]
        except KeyError:
            return None

    def has_team(self):
        """
        returns true if the student is on a team, false if the student is not on a team
        or if an exception is raised while looking up team
        """
        try:
            team = self.team
        except ObjectDoesNotExist:
            return False
        return bool(team)

    def valid_access_to_team_assessment(self):
        """
        A team-based ORA can be viewed by:
         - A student on a team
         - Course staff
         - Studio preview
        Students not on a team cannot access a team ORA
        """
        return self.is_course_staff or self.in_studio_preview or self.has_team()

    def add_team_submission_context(
        self, context, team_submission_uuid=None, individual_submission_uuid=None, transform_usernames=False
    ):
        """
        Adds team submission information to context dictionary, based on existing team submissions
        Specifically team name and team_usernames

        Params:
            - context (dict): a context dict for rendering a page that we will add values to
            - team_submission_uuid (string): [optional] the uuid of the team submission we want to add context info for
            - individual_submission_uuid (string): [optional] the uuid of an individual submission that's a part of
                                                   the team submission for which we want to add context info
            - transform_usernames (bool): [optional default: False] If False, context['team_usernames'] will be a list
                                          of username strings. If True, it will be a string, in the form
                                          "Username1, Username2, ... UsernameN, and UsernameN+1"

        One of team_submission_uuid and individual_submission_uuid are required, and if they are both provided,
        individual_submission_uuid will be ignored.
        """
        if not any((team_submission_uuid, individual_submission_uuid)):
            raise TypeError("One of team_submission_uuid or individual_submission_uuid must be provided")
        if team_submission_uuid:
            team_submission = get_team_submission(team_submission_uuid)
        elif individual_submission_uuid:
            team_submission = get_team_submission_from_individual_submission(individual_submission_uuid)

        team = self.teams_service.get_team_by_team_id(team_submission['team_id'])
        context['team_name'] = team.name

        student_ids = get_team_submission_student_ids(team_submission['team_submission_uuid'])
        usernames = [self.get_username(student_id) for student_id in student_ids]
        if transform_usernames:
            usernames = list_to_conversational_format(usernames)
        context['team_usernames'] = usernames

    def get_team_info(self):
        """
        Return a dict with team data if the user is on a team, or an
        empty dict otherwise.
        If we are course staff or in studio preview, return dummy data to
        render the page like a student would see
        """
        if self.in_studio_preview:
            return self.STAFF_OR_PREVIEW_INFO
        elif self.has_team():
            student_item_dict = self.get_student_item_dict()
            previous_team_name = None
            try:
                students_team_submission = get_team_submission_for_student(student_item_dict)
                if self.team.team_id != students_team_submission['team_id']:
                    previous_team_name = self.teams_service.get_team_by_team_id(
                        students_team_submission['team_id']
                    ).name
            except TeamSubmissionNotFoundError:
                pass

            return {
                'team_id': self.team.team_id,
                'team_name': self.team.name,
                'team_usernames': [user.username for user in self.team.users.all()],
                'team_url': self.teams_service.get_team_detail_url(self.team),
                'previous_team_name': previous_team_name,
            }
        elif self.is_course_staff:
            return self.STAFF_OR_PREVIEW_INFO
        else:
            return {}

    def get_anonymous_user_ids_for_team(self):
        if self.has_team():
            anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()
            user = self.get_real_user(anonymous_user_id)

            return self.teams_service.get_anonymous_user_ids_for_team(user, self.team)
        return None

    def get_team_submission_uuid_from_individual_submission_uuid(self, individual_submission_uuid):
        """
        Given an individual submission uuid, return the uuid of the related team submission
        """
        team_submission = get_team_submission_from_individual_submission(individual_submission_uuid)
        return team_submission['team_submission_uuid']

    def does_team_have_submission(self, team_id):
        try:
            student_item_dict = self.get_student_item_dict()
            get_team_submission_for_team(
                student_item_dict['course_id'],
                student_item_dict['item_id'],
                team_id
            )
            # If there's no submission, we will raise a TeamSubmissionNotFoundError
            return True
        except TeamSubmissionNotFoundError:
            return False
