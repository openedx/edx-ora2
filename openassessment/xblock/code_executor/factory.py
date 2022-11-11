import epicbox

from typing import Dict, List

from .constants import DEFAULT_LIMITS
from .config import get_all_code_executor_configs, get_all_epicbox_profiles
from .interface import CodeExecutor


epicbox.configure(get_all_epicbox_profiles())


CODE_EXECUTOR_CONFIGS = get_all_code_executor_configs()
CODE_EXECUTOR_CONFIG_ID_MAP = {config['id']: config for config in CODE_EXECUTOR_CONFIGS}


class CodeExecutorFactory:
    @staticmethod
    def get_code_executor(
        code_executor_id: str,
        source_code: str,
        files: List[Dict[str, bytes]] = [],
        limits: Dict[str, int] = DEFAULT_LIMITS,
        **kwargs
    ) -> CodeExecutor:
        config = CODE_EXECUTOR_CONFIG_ID_MAP.get(code_executor_id)
        if not config:
            raise Exception('No executor found for id')
        klass = config.get('class')
        if klass:
            return klass(source_code=source_code, files=files, limits=limits, **kwargs)
