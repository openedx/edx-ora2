"""
This module holds all of the deprecated grader code refactored into executors.
"""
import os
import re
import shutil
import subprocess
import uuid

from abc import ABC, abstractmethod
from typing import Dict, List, Union

from openassessment.xblock.enums import CodeExecutorOption

from ..exceptions import CodeCompilationError
from ..interface import CodeExecutor


class ServerShellCodeExecutorBase(ABC):
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
        # Since this executor is deprecated, we no longer need to complete the implementation.
        raise NotImplementedError()

    def run_input_from_file(self, name: str) -> dict:
        return self.execute_code(
            self.code_file_name, self.code_file_path, name, self.limits.get('cputime')
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
    def execute_code(self, code_file_name, code_file_path, input_file, timeout=10):
        pass

    def write_code_file(self, source_code, full_code_file_name):
        """
        accepts code and file name to where the code will be written.
        """
        f = open(full_code_file_name, 'w')
        f.write(source_code)
        f.close()


class JavaServerShellCodeExecutor(ServerShellCodeExecutorBase, CodeExecutor):
    display_name = 'Java 8'
    language = 'java'
    version = '8'

    id = CodeExecutorOption.ServerShell.value + '-' + CodeExecutor.create_id('java', '8')

    SOURCE_FILE_PATH_TEMPLATE = '{path}.java'

    def __init__(
        self,
        source_code: str,
        files: List[Dict[str, Union[str, bytes]]] = [],
        limits: Dict[str, int] = None,
        **kwargs
    ) -> None:
        super().__init__(source_code, files, limits, **kwargs)
        self.source_code = self.update_java_code(self.source_code, self.code_file_name)

    def execute_code(self, code_file_name, code_file_path, input_file, timeout=10):
        return self.run_java_code(code_file_name, timeout, input_file)

    def run_java_code(self, code_file_name, timeout, code_input_file=None):
        filename_with_lang_extension = '{}{}/{}.{}'.format(
            self.__TMP_DATA_DIR__, code_file_name, code_file_name, 'java'
        )
        compilation_command = 'javac -cp {0} {1}'.format(
            self.__SECRET_DATA_DIR__ + 'json-simple-1.1.1.jar', filename_with_lang_extension
        )
        execution_command = 'java -cp {} {}'.format(
            self.__TMP_DATA_DIR__
            + code_file_name
            + ':'
            + self.__SECRET_DATA_DIR__
            + 'json-simple-1.1.1.jar',
            code_file_name,
        )
        if code_input_file:
            execution_command += ' {}'.format(code_input_file)
        self.run_as_subprocess(compilation_command, compiling=True)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)

    def update_java_code(self, source_code, code_file_name):
        """
        Rewrite java code to have public class name replaced with the uuid generated name.
        """
        return re.sub(
            'public class (.*) {', 'public class {0} {{'.format(code_file_name), source_code
        )


class CppServerShellCodeExecutor(ServerShellCodeExecutorBase, CodeExecutor):
    display_name = 'C++ 17'
    language = 'cpp'
    version = '17'

    id = CodeExecutorOption.ServerShell.value + '-' + CodeExecutor.create_id('cpp', '17')

    SOURCE_FILE_PATH_TEMPLATE = '{path}.cpp'

    def execute_code(self, code_file_name, code_file_path, input_file, timeout=10):
        return self.run_cpp_code(code_file_path, timeout, input_file)

    def run_cpp_code(self, code_file, timeout, code_input_file=None):
        """
        Wrapper to run C++ code.
        Args:
            code_file(str): path to code file
            timeout(int): time after which the code execution will be forced-kill.
            code_input_file(str): Optional parameter, path to the input file that will be provided to code file.

        Returns:
            str output of the code execution
        """
        compiled_file_path = code_file + '.o'
        if not compiled_file_path.startswith('/'):
            compiled_file_path = '/' + compiled_file_path

        compilation_command = (
            'g++ ' + code_file + ' -o ' + compiled_file_path + ' -lcurl -std=gnu++17'
        )
        self.run_as_subprocess(compilation_command, compiling=True)

        execution_command = compiled_file_path
        if code_input_file:
            execution_command += ' {}'.format(code_input_file)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)


class PythonServerShellCodeExecutor(ServerShellCodeExecutorBase, CodeExecutor):
    display_name = 'Python 3.5'
    language = 'python'
    version = '3.5.2'

    id = CodeExecutorOption.ServerShell.value + '-' + CodeExecutor.create_id('python', '3.5.2')

    SOURCE_FILE_PATH_TEMPLATE = '{path}.py'

    def execute_code(self, code_file_name, code_file_path, input_file, timeout=10):
        return self.run_python_code(code_file_path, timeout, input_file)

    def run_python_code(self, code_file, timeout, code_input_file=None):
        """
        Wrapper to run python code.
        Args:
            code_file(str): path to code file
            timeout(int): time after which the code execution will be forced-kill.
            code_input_file(str): Optional parameter, path to the input file that will be provided to code file.

        Returns:
            str output of the code execution
        """
        execution_command = 'python3 ' + code_file
        if code_input_file:
            execution_command += ' {}'.format(code_input_file)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)


class JavascriptServerShellCodeExecutor(ServerShellCodeExecutorBase, CodeExecutor):
    display_name = 'Javascript (NodeJS 12)'
    language = 'javascript'
    version = 'nodejs-12.22.9'

    id = (
        CodeExecutorOption.ServerShell.value
        + '-'
        + CodeExecutor.create_id('javascript', 'nodejs-12.22.9')
    )

    SOURCE_FILE_PATH_TEMPLATE = '{path}.js'

    def execute_code(self, code_file_name, code_file_path, input_file, timeout=10):
        return self.run_nodejs_code(code_file_path, timeout, input_file)

    def run_nodejs_code(self, code_file, timeout, code_input_file=None):
        """
        Wrapper to run nodejs code.
        Args:
            code_file(str): path to code file
            timeout(int): time after which the code execution will be forced-kill.
            code_input_file(str): Optional parameter, path to the input file that will be provided to code file.

        Returns:
            str output of the code execution
        """
        execution_command = 'node ' + code_file
        if code_input_file:
            execution_command += ' {}'.format(code_input_file)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)
