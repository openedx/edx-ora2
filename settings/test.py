from .base import *

# Turn on the peer configurable grading feature toggle, which allows instructors
# to set the grading strategy for peer assessments. This feature is disabled by
# default, but we enable it so we test that default values are set correctly.
FEATURES["ENABLE_ORA_PEER_CONFIGURABLE_GRADING"] = True
