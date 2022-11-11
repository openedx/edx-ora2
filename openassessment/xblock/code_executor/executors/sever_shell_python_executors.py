from .server_shell_mixin import ServerShellCodeExecutorMixin

from openassessment.xblock.enums import CodeExecutorOption

from ..interface import CodeExecutor


class PythonServerShellCodeExecutor(ServerShellCodeExecutorMixin, CodeExecutor):
    display_name = 'Python 3.5'
    language = 'python'
    version = '3.5.2'

    id = CodeExecutorOption.ServerShell.value + '-' + CodeExecutor.create_id('python', '3.5.2')

    SOURCE_FILE_PATH_TEMPLATE = '{path}.py'

    def execute_code(
        self, code_file_name, code_file_path, input_file=None, stdin=None, timeout=10
    ):
        return self.run_python_code(code_file_path, timeout, input_file, stdin)

    def run_python_code(self, code_file, timeout, code_input_file=None, stdin=None):
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
        if stdin:
            execution_command = "echo '{}' | {}".format(stdin, execution_command)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)
