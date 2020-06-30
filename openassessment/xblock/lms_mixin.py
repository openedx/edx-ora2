"""
Fields and methods used by the LMS and Studio.
"""
from xblock.fields import DateTime, Dict, Float, Scope, String


class GroupAccessDict(Dict):
    """Special Dict class for serializing the group_access field"""
    def from_json(self, access_dict):  # pylint: disable=arguments-differ
        if access_dict is not None:
            return {int(k): access_dict[k] for k in access_dict}
        return None

    def to_json(self, access_dict):  # pylint: disable=arguments-differ
        if access_dict is not None:
            return {str(k): access_dict[k] for k in access_dict}
        return None


class LmsCompatibilityMixin:
    """
    Extra fields and methods used by LMS/Studio.
    """
    # Studio the default value for this field to show this XBlock
    # in the list of "Advanced Components"
    display_name = String(
        default="Open Response Assessment", scope=Scope.settings,
        help="Display name"
    )

    start = DateTime(
        default=None, scope=Scope.settings,
        help="ISO-8601 formatted string representing the start date of this assignment."
    )

    due = DateTime(
        default=None, scope=Scope.settings,
        help="ISO-8601 formatted string representing the due date of this assignment."
    )

    weight = Float(
        display_name="Problem Weight",
        help=("Defines the number of points each problem is worth. "
              "If the value is not set, the problem is worth the sum of the "
              "option point values."),
        values={"min": 0, "step": .1},
        scope=Scope.settings
    )

    group_access = GroupAccessDict(
        help=(
            "A dictionary that maps which groups can be shown this block. The keys "
            "are group configuration ids and the values are a list of group IDs. "
            "If there is no key for a group configuration or if the set of group IDs "
            "is empty then the block is considered visible to all. Note that this "
            "field is ignored if the block is visible_to_staff_only."
        ),
        default={},
        scope=Scope.settings,
    )

    icon_class = "problem"

    def has_dynamic_children(self):
        """Do we dynamically determine our children? No, we don't have any.

        The LMS wants to know this to see if it has to instantiate our module
        and query it to find the children, or whether it can just trust what's
        in the static (cheaper) children listing.
        """
        return False

    @property
    def has_score(self):
        """Are we a scored type (read: a problem). Yes.

        For LMS Progress page/grades download purposes, we're always going to
        have a score, even if it's just 0 at the start.
        """
        return True

    def max_score(self):
        """The maximum raw score of our problem.

        Called whenever the LMS knows that something is scorable, but finds no
        recorded raw score for it (i.e. the student hasn't done it). In that
        case, the LMS knows that the earned score is 0, but it doesn't know what
        to put in the denominator. So we supply it with the total number of
        points that it is possible for us to earn -- the sum of the highest
        pointed options from each criterion.

        Note that if we have already recorded a score in submissions, this
        method will never be called. So it's perfectly possible for us to have
        10/10 on the progress page and a 12 returning from this method if our
        10/10 score was earned in the past and the problem has changed since
        then.
        """
        return sum(
            max(option["points"] for option in criterion["options"])
            if criterion["options"] else 0
            for criterion in self.rubric_criteria
        )
