import logging

from edx_rest_api_client.client import EdxRestApiClient

from openassessment.assessment.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    BASE_URL,
)

logger = logging.getLogger(__name__)


class AIAssessmentAPI(object):
    """
    API to Assess response using ai.
    """
    def __init__(self):
        self.access_token, self.access_token_expiration = self._get_access_token()
        self.api_client = self.get_api_client()

    @classmethod
    def _get_access_token(cls):
        """
        Uses edx_rest_api_client to get the access token.
        """
        return EdxRestApiClient.get_oauth_access_token(
            BASE_URL,
            CLIENT_ID,
            CLIENT_SECRET,
        )

    def get_api_client(self):
        """
        Gets the api client.
        """
        return EdxRestApiClient(BASE_URL, oauth_access_token=self.access_token)
