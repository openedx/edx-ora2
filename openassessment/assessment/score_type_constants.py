""" Constant strings used to identify what type of score an Assessment is. Used in the 'score_type' field """

from django.utils.translation import gettext as _

PEER_TYPE = "PE"
SELF_TYPE = "SE"
STAFF_TYPE = "ST"


def score_type_to_string(score_type: str) -> str:
    """
    Converts the given score type into its string representation.

    Args:
        score_type (str): System representation of the score type.

    Returns:
        (str) Representation of score_type as needed in Staff Grader Template.
    """
    SCORE_TYPE_MAP = {
        PEER_TYPE: _("Peer"),
        SELF_TYPE: _("Self"),
        STAFF_TYPE: _("Staff"),
    }
    return SCORE_TYPE_MAP.get(score_type, _("Unknown"))
