from abc import ABC, abstractmethod
from typing import Dict, List


class CodeExecutor(ABC):
    """
    Interface for all types of code executors. Code executors must have this class as one of their
    ancestor classes, otherwise the code executor will not be automatically registered.
    """

    @staticmethod
    def create_id(language: str, version: str) -> str:
        """A utility function that combines language and version to form an id string.

        Args:
            language (str): Programming language
            version (str): Language version

        Returns:
            str: A string concatenation of the parameters.
        """
        return '{}:{}'.format(language.lower(), version.lower())

    @classmethod
    @abstractmethod
    def get_config(cls) -> dict:
        """Returns the config for this executor. The structure is as follows.
        
            {
                'id': 'id',
                'display_name': '',
                'language': '',
                'version': '',
                'profiles': [
                    <instance of epicbox.Profile>
                ]
            }

        Returns:
            dict: config object.
        """
        pass

    @abstractmethod
    def __init__(
        self,
        source_code: str,
        files: List[Dict[str, bytes]] = [],
        limits: Dict[str, int] = None,
        *args,
        **kwargs
    ) -> None:
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    @abstractmethod
    def run_input(self, input: str) -> dict:
        """Run code with standard input `input`.

        Args:
            input (str): Input piped to stdin.

        Returns:
            dict: Execution response. The structure is as follows:
            {
                'exit_code': 0, 
                'stdout': b'4\n', 
                'stderr': b'', 
                'duration': 0.095318, 
                'timeout': False, 
                'oom_killed': False
            }
        """
        pass

    @abstractmethod
    def run_input_from_file(self, name: str) -> dict:
        """Run code with the file `name` passed as an argument.

        Args:
            name (str): Name of the file. This is the same name provided in __init__ for files.

        Returns:
            dict: Execution response. The structure is as follows:
            {
                'exit_code': 0, 
                'stdout': b'4\n', 
                'stderr': b'', 
                'duration': 0.095318, 
                'timeout': False, 
                'oom_killed': False
            }
        """
        pass
