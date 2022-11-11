import epicbox

from abc import ABC
from typing import Dict, List
from uuid import uuid4

from ..exceptions import CodeCompilationError, WorkingDirectoryNotInitializedException


class ScriptedLanguageExecutorMixin(ABC):
    """
    All scripted languages' code is run in a similar manner. You take the interpreter like python
    and pass it the script and arguments.
    
    This mixin helps alleviate some of the boilerplate code. To aid with this nobel endeavor, a few
    class-level (static) variables are defined. Add this mixin to your class and override those 
    variables, and you'll have a complete implementation.
    
    For docs of individual functions, please see CodeExecutor class.
    """

    docker_image = ''
    language = ''
    version = ''
    display_name = ''

    id = ''

    SOURCE_FILE_NAME_TEMPLATE = '{name}'
    RUN_COMMAND_STDIN_INPUT_TEMPLATE = '{source_file}'
    RUN_COMMAND_FILE_INPUT_TEMPLATE = '{source_file} {input_file}'

    @classmethod
    def get_config(cls) -> dict:
        return {
            'id': cls.id,
            'display_name': cls.display_name,
            'language': cls.language,
            'version': cls.version,
            'profiles': [
                epicbox.Profile(name=cls.id, docker_image=cls.docker_image, read_only=True,)
            ],
        }

    def __init__(
        self,
        source_code: str,
        files: List[Dict[str, bytes]] = [],
        limits: Dict[str, int] = None,
        **kwargs
    ) -> None:
        self.source_file_name = self.SOURCE_FILE_NAME_TEMPLATE.format(name=uuid4())
        self.limits = limits
        self.files = files + [
            {'name': self.source_file_name, 'content': bytes(source_code, 'utf-8')}
        ]
        self.working_directory_context_manager = epicbox.working_directory()
        self.working_directory = None

    def __enter__(self):
        self.working_directory = self.working_directory_context_manager.__enter__()
        # Run this once to setup the working directory.
        epicbox.run(
            self.id, files=self.files, workdir=self.working_directory,
        )

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.working_directory_context_manager.__exit__(exc_type, exc_value, exc_tb)

    def _check_working_directory_creation(self):
        if self.working_directory is None:
            raise WorkingDirectoryNotInitializedException(
                'Working directory not created. '
                'Please use code executor with a context manager.'
            )

    def run_input(self, input: str) -> dict:
        self._check_working_directory_creation()
        run_command = self.RUN_COMMAND_STDIN_INPUT_TEMPLATE.format(
            source_file=self.source_file_name,
        )
        result = epicbox.run(
            self.id,
            run_command,
            stdin=input,
            workdir=self.working_directory,
            limits=self.limits,
        )
        return result

    def run_input_from_file(self, name: str) -> dict:
        self._check_working_directory_creation()
        run_command = self.RUN_COMMAND_FILE_INPUT_TEMPLATE.format(
            source_file=self.source_file_name, input_file=name,
        )
        result = epicbox.run(
            self.id, run_command, workdir=self.working_directory, limits=self.limits,
        )
        return result


class CompiledLanguageExecutorMixin(ABC):
    """
    All compiled languages' code is run in a similar manner. You take the source, compile it, and
    and then run the executable.
    
    This mixin helps alleviate some of the boilerplate code. To aid with this nobel endeavor, a few
    class-level (static) variables are defined. Add this mixin to your class and override those 
    variables, and you'll have a complete implementation.
    
    For docs of individual functions, please see CodeExecutor class.
    """

    docker_image = ''
    language = ''
    version = ''
    display_name = ''

    id = ''

    SOURCE_FILE_NAME_TEMPLATE = '{name}'
    EXECUTABLE_FILE_NAME_TEMPLATE = '{name}'
    COMPILE_COMMAND_TEMPLATE = '{source_file} {executable_file}'
    RUN_COMMAND_STDIN_INPUT_TEMPLATE = '{executable_file}'
    RUN_COMMAND_FILE_INPUT_TEMPLATE = '{executable_file} {input_file}'

    @classmethod
    def get_config(cls) -> dict:
        return {
            'id': cls.id,
            'display_name': cls.display_name,
            'language': cls.language,
            'version': cls.version,
            'profiles': [
                epicbox.Profile(
                    name='{}-compile'.format(cls.id), docker_image=cls.docker_image,
                ),
                epicbox.Profile(
                    name='{}-run'.format(cls.id),
                    docker_image=cls.docker_image,
                    user='sandbox',
                    read_only=True,
                ),
            ],
        }

    def __init__(
        self,
        source_code: str,
        files: List[Dict[str, bytes]] = [],
        limits: Dict[str, int] = None,
        **kwargs
    ) -> None:
        self.compile_profile_name = '{}-compile'.format(self.id)
        self.run_profile_name = '{}-run'.format(self.id)

        self.source_file_name = self.SOURCE_FILE_NAME_TEMPLATE.format(name=uuid4())
        self.executable_file_name = self.EXECUTABLE_FILE_NAME_TEMPLATE.format(name=uuid4())
        self.limits = limits
        self.files = files + [
            {'name': self.source_file_name, 'content': bytes(source_code, 'utf-8'),}
        ]
        self.working_directory_context_manager = epicbox.working_directory()
        self.working_directory = None

    def __enter__(self):
        self.working_directory = self.working_directory_context_manager.__enter__()

        # Compile code.
        results = epicbox.run(
            self.compile_profile_name,
            command=self.COMPILE_COMMAND_TEMPLATE.format(
                source_file=self.source_file_name, executable_file=self.executable_file_name,
            ),
            files=self.files,
            workdir=self.working_directory,
            limits=self.limits,
        )
        if results['exit_code'] != 0:
            message = results['stderr'].decode('utf-8')
            if results['timeout']:
                message = 'Compilation time limit exceeded.'
            elif results['oom_killed']:
                message = 'Compilation memory limit exceeded.'

            raise CodeCompilationError(message=message)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.working_directory_context_manager.__exit__(exc_type, exc_value, exc_tb)

    def _check_working_directory_creation(self):
        if self.working_directory is None:
            raise WorkingDirectoryNotInitializedException(
                'Working directory not created. '
                'Please use code executor with a context manager.'
            )

    def run_input(self, input: str) -> dict:
        self._check_working_directory_creation()
        run_command = self.RUN_COMMAND_STDIN_INPUT_TEMPLATE.format(
            executable_file=self.executable_file_name,
        )
        result = epicbox.run(
            self.run_profile_name,
            run_command,
            stdin=input,
            workdir=self.working_directory,
            limits=self.limits,
        )
        return result

    def run_input_from_file(self, name: str) -> dict:
        self._check_working_directory_creation()
        run_command = self.RUN_COMMAND_FILE_INPUT_TEMPLATE.format(
            executable_file=self.executable_file_name, input_file=name,
        )
        result = epicbox.run(
            self.run_profile_name,
            run_command,
            workdir=self.working_directory,
            limits=self.limits,
        )
        return result
