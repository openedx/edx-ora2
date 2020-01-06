""" Mixin to encapsulate teams-related behavior """
import logging

from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist
from xblock.exceptions import NoSuchServiceError

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TeamMixin(object):
    """Team Mixin introducing all teams-related functionality."""

    STAFF_OR_PREVIEW_INFO = {
        'team_name': '< TEAM NAME >',
        'team_usernames': ['< USERNAMES >'],
        'team_url': '#TEAM_URL',
    }
    @cached_property
    def teams_service(self):
        try:
            return self.runtime.service(self, 'teams')
        except NoSuchServiceError:
            logger.error(u'{}: Teams service unavailable'.format(self.location))

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
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()
        user = self.get_real_user(anonymous_user_id)
        if not user:
            logger.error(u'{}: User lookup for anonymous_user_id {} failed'.format(self.location, anonymous_user_id))
            raise ObjectDoesNotExist()
        team = self.teams_service.get_team(user, self.course_id)
        return team

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
        Return a dict with team data if the user is on a team, None otherwise
        If we are course staff or in studio preview, return dummy data to
        render the page like a student would see
        """
        if self.has_team():
            return {
                'team_name': self.team.name,
                'team_usernames': [user.username for user in self.team.users.all()],
                'team_url': self.teams_service.get_team_detail_url(self.team),
            }
        elif self.is_course_staff or self.in_studio_preview:
            return self.STAFF_OR_PREVIEW_INFO
        else:
            return None
