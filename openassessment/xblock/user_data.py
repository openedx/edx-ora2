"""
Retrieve user-specific data
"""


def get_user_preferences(user_service):
    """
    Returns the preferred language and timezone for the current user, if specified, or None if not.

    :param user_service: XblockUserService
    """
    user_preferences = {
        'user_language': None,
        'user_timezone': None
    }
    retrieved_preferences = user_service.get_current_user().opt_attrs.get('edx-platform.user_preferences')

    if retrieved_preferences is not None:
        user_preferences['user_timezone'] = retrieved_preferences.get('time_zone')
        user_preferences['user_language'] = retrieved_preferences.get('pref-lang')

    return user_preferences
