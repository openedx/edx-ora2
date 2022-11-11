from .server_shell_mixin import ServerShellCodeExecutorMixin

from openassessment.xblock.enums import CodeExecutorOption

from ..interface import CodeExecutor


class CppServerShellCodeExecutor(ServerShellCodeExecutorMixin, CodeExecutor):
    display_name = 'C++ 17'
    language = 'cpp'
    version = '17'

    id = CodeExecutorOption.ServerShell.value + '-' + CodeExecutor.create_id('cpp', '17')

    SOURCE_FILE_PATH_TEMPLATE = '{path}.cpp'

    def execute_code(
        self, code_file_name, code_file_path, input_file=None, stdin=None, timeout=10
    ):
        return self.run_cpp_code(code_file_path, timeout, input_file, stdin)

    def run_cpp_code(self, code_file, timeout, code_input_file=None, stdin=None):
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
        if stdin:
            execution_command = "echo '{}' | {}".format(stdin, execution_command)
        return self.run_as_subprocess(execution_command, running_code=True, timeout=timeout)
