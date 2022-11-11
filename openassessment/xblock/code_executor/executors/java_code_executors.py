from .mixins import CompiledLanguageExecutorMixin

from ..interface import CodeExecutor


class JavaCodeExecutor(CompiledLanguageExecutorMixin, CodeExecutor):
    docker_image = 'stepik/epicbox-java:17.0.1'
    language = 'java'
    version = '17.0.1'
    display_name = 'Java 17'

    id = CodeExecutor.create_id('java', '17.0.1')

    SOURCE_FILE_NAME_TEMPLATE = 'Main.java'
    EXECUTABLE_FILE_NAME_TEMPLATE = 'Main'
    COMPILE_COMMAND_TEMPLATE = 'javac {source_file}'
    RUN_COMMAND_STDIN_INPUT_TEMPLATE = 'java {executable_file}'
    RUN_COMMAND_FILE_INPUT_TEMPLATE = 'java {executable_file} {input_file}'
