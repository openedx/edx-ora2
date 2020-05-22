""" Mixin to encapsulate teams-related behavior """
import logging

from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TeamMixin:
    """Team Mixin introducing all teams-related functionality."""

    STAFF_OR_PREVIEW_INFO = {
        'team_name': '< TEAM NAME >',
        'team_usernames': ['< USERNAMES >'],
        'team_url': '#TEAM_URL',
    }

    def is_team_assignment(self):
        # pylint: disable=no-member
        return self.teams_enabled and self.team_submissions_enabled

    @cached_property
    def teams_service(self):
        try:
            return self.runtime.service(self, 'teams')
        except NoSuchServiceError:
            logger.error(u'{}: Teams service unavailable'.format(self.location))
            raise

    @cached_property
    def teams_configuration_service(self):
        try:
            return self.runtime.service(self, 'teams_configuration')
        except NoSuchServiceError:
            logger.error(u'{}: Teams Configuration service unavailable'.format(self.location))
            raise

    def get_team_for_anonymous_user(self, anonymous_user_id):
        """
        For course_id associated with this ORA block, returns the provided user's
        CourseTeam, or None if the user is not a member of a team in this course.
        Raises:
            - NoSuchServiceError if the teams service is unavailable
            - ObjectDoesNotExist if the user associated with `anonymous_user_id`
                                    can not be found
        """
        user = self.get_real_user(anonymous_user_id)
        if not user:
            logger.error(u'{}: User lookup for anonymous_user_id {} failed'.format(self.location, anonymous_user_id))
            raise ObjectDoesNotExist()
        team = self.teams_service.get_team(user, self.course_id, self.selected_teamset_id)
        return team

    @cached_property
    def team(self):
        """
        For the user and course_id associated with this ORA block, returns the user's
        CourseTeam, or None if the user is not a member of a team in this course.
        Raises:
            - NoSuchServiceError if the teams service is unavailable
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
            return {
                'team_id': self.team.team_id,
                'team_name': self.team.name,
                'team_usernames': [user.username for user in self.team.users.all()],
                'team_url': self.teams_service.get_team_detail_url(self.team),
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
