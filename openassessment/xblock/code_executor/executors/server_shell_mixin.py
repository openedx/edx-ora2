"""
This module holds deprecated grader code refactored into executors.
"""
import os
import shutil
import subprocess
import uuid

from abc import ABC, abstractmethod
from typing import Dict, List, Union

from ..exceptions import CodeCompilationError


class ServerShellCodeExecutorMixin(ABC):
    __SECRET_DATA_DIR__ = '/grader_data/'
    __TMP_DATA_DIR__ = '/tmp/'

    display_name = ''
    language = ''
    version = ''

    id = ''

    SOURCE_FILE_PATH_TEMPLATE = '{path}'

    @classmethod
    def get_config(cls) -> dict:
        return {
            'id': cls.id,
            'display_name': cls.display_name,
            'language': cls.language,
            'version': cls.version,
        }

    def __init__(
        self,
        source_code: str,
        files: List[Dict[str, Union[str, bytes]]] = [],
        limits: Dict[str, int] = None,
        **kwargs
    ) -> None:
        code_file_name = 'auto_generated_code_file_' + str(uuid.uuid4()).replace('-', '')
        code_file_path = self.__TMP_DATA_DIR__ + code_file_name + '/' + code_file_name

        self.source_code = source_code
        self.files = files
        self.limits = limits
        self.code_file_path = self.SOURCE_FILE_PATH_TEMPLATE.format(path=code_file_path)
        self.code_file_name = code_file_name

    def __enter__(self):
        if not os.path.exists(self.__TMP_DATA_DIR__ + self.code_file_name):
            os.mkdir(self.__TMP_DATA_DIR__ + self.code_file_name)

        self.write_code_file(self.source_code, self.code_file_path)

    def __exit__(self, exc_type, exc_value, exc_tb):
        shutil.rmtree(self.__TMP_DATA_DIR__ + self.code_file_name)

    def run_input(self, input: str) -> dict:
        return self.execute_code(
            self.code_file_name,
            self.code_file_path,
            input_file=None,
            stdin=input,
            timeout=self.limits.get('cputime'),
        )

    def run_input_from_file(self, name: str) -> dict:
        return self.execute_code(
            self.code_file_name,
            self.code_file_path,
            input_file=name,
            stdin=None,
            timeout=self.limits.get('cputime'),
        )

    def run_as_subprocess(self, cmd, compiling=False, running_code=False, timeout=None):
        """
        runs the subprocess and execute the command. if timeout is given kills the
        process after the timeout period has passed. compiling and running code flags
        helps to return related message in exception
        """

        if timeout:
            cmd = 'timeout --signal=SIGKILL {0} {1}'.format(timeout, cmd)

        output, error = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        ).communicate()

        result = {
            'exit_code': 0,
            'stdout': output,
            'stderr': b'',
            'duration': None,  # Not supported
            'timeout': False,
            'oom_killed': None,  # Not supported
        }

        if error and compiling:
            raise CodeCompilationError(message=error.decode('utf-8'))

        if error and running_code and 'Killed' in error.decode('utf-8'):
            result['exit_code'] = 1
            result['stderr'] = error
            result['timeout'] = True
        elif error and running_code:
            result['exit_code'] = 1
            result['stderr'] = error

        return result

    @abstractmethod
    def execute_code(
        self, code_file_name, code_file_path, input_file=None, stdin=None, timeout=10
    ):
        pass

    def write_code_file(self, source_code, full_code_file_name):
        """
        accepts code and file name to where the code will be written.
        """
        f = open(full_code_file_name, 'w')
        f.write(source_code)
        f.close()
