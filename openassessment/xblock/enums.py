from enum import Enum


class CodeExecutorOption(Enum):
    ServerShell = 'server_shell'
    Epixbox = 'epicbox'
    CodeJail = 'codejail'

    @classmethod
    def values(cls):
        return [option.value for option in cls]

    @classmethod
    def names(cls):
        return [option.name for option in cls]   
