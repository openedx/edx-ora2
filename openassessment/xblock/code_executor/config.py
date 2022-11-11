import epicbox

from typing import List

from .interface import CodeExecutor


def _get_all_subclasses(cls):
    """
    Use reflection to find all sub classes of class.

    Returns: List of classes.
    """
    return list(
        set(cls.__subclasses__()).union(
            [
                sub_class
                for klass in cls.__subclasses__()
                for sub_class in _get_all_subclasses(klass)
            ]
        )
    )


def get_all_code_executor_configs() -> List[dict]:
    """
    Finds all subclasses of CodeExecutor and returns their config dicts.

    Returns:
        List[dict]: All CodeExecutor configs.
    """
    all_config_ids = set()
    all_configs = []

    for sub_class in _get_all_subclasses(CodeExecutor):
        config = sub_class.get_config()
        if not config:
            continue
        if config.get('id') is None:
            raise Exception('CodeExecutor without an ID')
        elif config['id'] in all_config_ids:
            raise Exception('Multiple executors registered with the same ID')
        else:
            config['class'] = sub_class
            all_configs.append(config)
            all_config_ids.add(config.get('id'))

    return all_configs


def get_all_epicbox_profiles() -> List[epicbox.Profile]:
    """
    Returns all profiles fetched from all the code executors' configs.
    """
    configs = get_all_code_executor_configs()
    return [profile for config in configs for profile in config.get('profiles', [])]
