from .mixins import CompiledLanguageExecutorMixin

from ..interface import CodeExecutor


class CppCodeExecutor(CompiledLanguageExecutorMixin, CodeExecutor):
    docker_image = 'stepik/epicbox-gcc:10.2.1'
    language = 'cpp'
    version = '20'
    display_name = 'C++ 20 (gcc 10.2.1)'

    id = CodeExecutor.create_id('cpp', '20')

    SOURCE_FILE_NAME_TEMPLATE = '{name}.cpp'
    EXECUTABLE_FILE_NAME_TEMPLATE = '{name}.out'
    COMPILE_COMMAND_TEMPLATE = 'g++ -static -o {executable_file} -std=gnu++2a {source_file}'
    RUN_COMMAND_STDIN_INPUT_TEMPLATE = './{executable_file}'
    RUN_COMMAND_FILE_INPUT_TEMPLATE = './{executable_file} {input_file}'
