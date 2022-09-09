from .mixins import ScriptedLanguageExecutorMixin

from ..interface import CodeExecutor


class JavascriptCodeExecutor(ScriptedLanguageExecutorMixin, CodeExecutor):
    docker_image = 'node:lts-alpine3.16'
    language = 'javascript'
    version = 'nodejs-3.16'
    display_name = 'Javascript (NodeJS 3.16)'

    id = CodeExecutor.create_id('javascript', 'nodejs-3.16')

    SOURCE_FILE_NAME_TEMPLATE = '{name}.js'
    RUN_COMMAND_STDIN_INPUT_TEMPLATE = 'node {source_file}'
    RUN_COMMAND_FILE_INPUT_TEMPLATE = 'node {source_file} {input_file}'
