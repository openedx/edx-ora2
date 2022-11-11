from enum import Enum


class CodeExecutorOption(Enum):
    ServerShell = 'server_shell'
    Epicbox = 'epicbox'

    @classmethod
    def values(cls):
        return [option.value for option in cls]

    @classmethod
    def names(cls):
        return [option.name for option in cls]   
