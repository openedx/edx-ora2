# pylint: disable=import-error
"""
A module for containing various inline runtime class imports
Functions in this module should take no args and simply import and return the <class> object.
"""


def import_block_structure_transformers():
    """
    Helper method that imports BlockStructureTransformers from edx platform at runtime.
    """
    from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers
    return BlockStructureTransformers


def import_course_waffle_flag():
    """
    Helper method that imports CourseWaffleFlag from edx-platform at runtime.
    https://github.com/openedx/edx-platform/blob/master/openedx/core/djangoapps/waffle_utils/__init__.py#L345
    """
    from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag
    return CourseWaffleFlag


def import_external_id():
    """
    Helper method that imports ExternalId from edx platform at runtime.
    """
    from openedx.core.djangoapps.external_user_ids.models import ExternalId
    return ExternalId


def import_waffle_flag():
    """
    Helper method that imports WaffleFlag from edx_toggles at runtime.
    """
    from edx_toggles.toggles import WaffleFlag
    return WaffleFlag
