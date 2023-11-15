"""
Constants used in the ORA MFE BFF
"""

# Request Errors
INCORRECT_PARAMETERS = "ERR_WRONG_PARAMS"
UNKNOWN_SUFFIX = "ERR_SUFFIX"
INACCESSIBLE_STEP = "ERR_INACCESSIBLE_STEP"

# Internal Errors
INTERNAL_EXCEPTION = "ERR_INTERNAL"
UNKNOWN_ERROR = "ERR_UNKNOWN"

# Studio Errors
IN_STUDIO_PREVIEW = "ERR_IN_STUDIO_PREVIEW"

# Assessment Errors
TRAINING_ANSWER_INCORRECT = "ERR_TRAINING_INCORRECT"
INVALID_STATE_TO_ASSESS = "ERR_INVALID_STATE_FOR_ASSESSMENT"

# Submission Errors
INVALID_RESPONSE_SHAPE = "ERR_INCORRECT_RESPONSE_SHAPE"
MULTIPLE_SUBMISSIONS = "ERR_MULTIPLE_SUBMISSIONS"
SUBMISSION_TOO_LONG = "ERR_SUBMISSION_TOO_LONG"
SUBMISSION_API_ERROR = "ERR_SUBMISSION_API"
EMPTY_ANSWER = "ERR_EMPTY_ANSWER"

# File Errors
DELETE_NOT_ALLOWED = "ERR_DELETE_NOT_ALLOWED"
UNABLE_TO_GENERATE_UPLOAD_URL = "ERR_UNABLE_TO_GENERATE_UPLOAD_URL"
TOO_MANY_UPLOADS = "ERR_TOO_MANY_UPLOADS"
UNSUPPORTED_FILETYPE = "ERR_UNSUPPORTED_FILETYPE"
FILE_NOT_FOUND = "ERR_FILE_NOT_FOUND"
