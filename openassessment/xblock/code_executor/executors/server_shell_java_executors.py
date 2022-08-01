import re

from typing import Dict, List, Union

from .server_shell_mixin import ServerShellCodeExecutorMixin

from openassessment.xblock.enums import CodeExecutorOption

from ..interface import CodeExecutor


class JavaServerShellCodeExecutor(ServerShellCodeExecutorMixin, CodeExecutor):
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

    def execute_code(
        self, code_file_name, code_file_path, input_file=None, stdin=None, timeout=10
    ):
        return self.run_java_code(code_file_name, timeout, input_file, stdin)

    def run_java_code(self, code_file_name, timeout, code_input_file=None, stdin=None):
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
        if stdin:
            execution_command = "echo '{}' | {}".format(stdin, execution_command)
        self.run_as_subprocess(compilation_command, compiling=True)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)

    def update_java_code(self, source_code, code_file_name):
        """
        Rewrite java code to have public class name replaced with the uuid generated name.
        """
        return re.sub(
            'public class (.*) {', 'public class {0} {{'.format(code_file_name), source_code
        )
