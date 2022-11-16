import glob
import logging
import os
import json

from uuid import uuid4

from tempfile import NamedTemporaryFile, TemporaryFile

from collections import OrderedDict
from openassessment.xblock.code_executor.exceptions import CodeCompilationError
from openassessment.xblock.code_executor.factory import (
    CODE_EXECUTOR_CONFIGS,
    CodeExecutorFactory,
)
from openassessment.xblock.enums import CodeExecutorOption
from openassessment.xblock.job_sample_grader.utils import (
    is_design_problem,
    get_error_response,
    truncate_error_output,
)

from litmustest_djangoapps.core.models import AssessmentQuestionXblockMapping

logger = logging.getLogger(__name__)


ALL_CODE_EXECUTORS = sorted(
    [
        {
            'name': config.get('display_name', config['id']),
            'value': config['id'],
            'language': config.get('language', config['id'].split(':')[0]),
        }
        for config in CODE_EXECUTOR_CONFIGS
    ],
    key=lambda x: x['name'],
)


class CodeGraderMixin(object):
    SERVER_SHELL_EXECUTORS = list(
        filter(
            lambda executor: executor['value'].startswith(
                CodeExecutorOption.ServerShell.value
            ),
            ALL_CODE_EXECUTORS,
        )
    )

    EPICBOX_EXECUTORS = list(
        filter(
            lambda executor: (
                not executor['value'].startswith(CodeExecutorOption.ServerShell.value)
            ),
            ALL_CODE_EXECUTORS,
        )
    )

    __SECRET_DATA_DIR__ = '/grader_data/'
    __TMP_DATA_DIR__ = '/tmp/'

    def get_code_grader_context(self):
        available_executors = []
        if self.executor == CodeExecutorOption.ServerShell.value:
            available_executors = self.SERVER_SHELL_EXECUTORS
        else:
            available_executors = self.EPICBOX_EXECUTORS

        return {
            'available_code_executors': available_executors,
        }

    def grade(self, response, add_staff_cases=False):
        """
        Set prerequisites and execute code.
            * Submission code is added in directory
            * File name is auto generated unique string
            * For designed problem simply code executes but for other problems code executed with
                test cases.
        Args:
            response (dict):
                problem_name(str)
                submission(str): code submitted by user
                executor_id(str): executor_id of the code executor to use
                add_staff_cases (bool, optional): Defaults to False.
        """
        problem_name = response['problem_name']
        source_code = response['submission']
        executor_id = response.get('executor_id')

        if executor_id is None or executor_id not in [
            e['value'] for e in self.get_code_grader_context()['available_code_executors']
        ]:
            return self.response_with_error_v2('No such language available.')

        output = []
        if is_design_problem(problem_name):
            try:
                output.append(self.run_design_code(executor_id, source_code=source_code))
            except CodeCompilationError as ex:
                output.extend(self.response_with_error_v2(ex.message))
        else:
            try:
                output.append(self.run_code('sample', executor_id, source_code, problem_name))
            except CodeCompilationError as ex:
                output.extend(self.response_with_error_v2(ex.message))
            if add_staff_cases:
                try:
                    output.append(self.run_code('staff', executor_id, source_code, problem_name))
                except CodeCompilationError as ex:
                    output.extend(self.response_with_error_v2(ex.message))

        return output

    def response_with_error_v2(self, error):
        """
        To make the incorrect language error compatible with per file test
        case run output.
        """
        return [get_error_response('sample', error)]

    def _executor_output_to_response_format(self, executor_output):
        response = {'output': '', 'error': '', 'exit_code': executor_output['exit_code']}

        if executor_output['timeout']:
            response['output'] = 'Time limit exceeded.'
        elif executor_output['oom_killed']:
            response['output'] = 'Memory limit exceeded.'
        elif executor_output['stderr']:
            response['output'] = truncate_error_output(
                executor_output['stderr'].decode('utf-8')
            )
        elif executor_output['stdout']:
            response['output'] = executor_output['stdout'].decode('utf-8')

        return response

    def read_test_cases_from_db(self, question, run_type):
        """
        Reads test cases from question model's metadata field
        """
        try:
            test_cases = json.loads(question.metadata).get(run_type, {})
        except:
            test_cases = question.metadata.get(run_type, {})

        test_case_files = []

        temporary_directory = os.path.join(self.__TMP_DATA_DIR__, self.__SECRET_DATA_DIR__.lstrip(os.sep))
        os.makedirs(temporary_directory, exist_ok=True)

        for case_number in sorted(test_cases.keys()):
            case = test_cases[case_number]
            test_case_tmp_file_name_prefix = str(uuid4());
            try:
                input_file = NamedTemporaryFile(
                    mode='w+',
                    prefix=test_case_tmp_file_name_prefix,
                    suffix='.in',
                    dir=temporary_directory,
                    delete=False
                )
                input_file.write(case['input'])
                input_file.close()

                expected_output_file = NamedTemporaryFile(
                    mode='w+',
                    prefix=test_case_tmp_file_name_prefix,
                    suffix='.out',
                    dir=temporary_directory,
                    delete=False
                )
                expected_output_file.write(case['output'])
                expected_output_file.close()
            except PermissionError as error:
                logger.error(
                    'The OS user "{}" does not have the permission to create temporary file under "{}". Error: {}'
                    .format(
                        os.getlogin(),
                        temporary_directory,
                        error
                    )
                )
                raise error

            test_case_files.append(
                {
                    'case_number': case_number,
                    'input_file': {
                        'name': input_file.name,
                        'content': bytes(case['input'], 'utf-8'),
                    },
                    'expected_output_file': {'name': expected_output_file.name},
                }
            )

        return test_case_files

    def read_test_cases_from_file(self, problem_name, run_type):
        """
        Reads test cases from grader_data file
        """
        test_case_paths = glob.glob(
            '{}{}/{}/*'.format(self.__SECRET_DATA_DIR__, problem_name, run_type)
        )

        # Sort the test cases based on the test number
        if test_case_paths:
            test_case_paths = sorted(
                test_case_paths, key=lambda test_case: int(test_case.split('/')[-1])
            )

        test_case_files = []

        for case in test_case_paths:
            case_number = int(case.split('/')[-1])
            input_file = '{}/input.in'.format(case)
            expected_output_file = '{}/output.out'.format(case)

            with open(input_file, 'rb') as file:
                input_content = file.read()

            test_case_files.append(
                {
                    'case_number': case_number,
                    'input_file': {
                        # Keeping the file names the same as host.
                        # This will allow us to use the same names
                        # for epicbox and server_shell.
                        'name': input_file,
                        'content': input_content,
                    },
                    'expected_output_file': {'name': expected_output_file},
                }
            )

        return test_case_files

    def run_code(self, run_type, executor_id, source_code, problem_name):
        """Run code for all test cases.

        Args:
            run_type (str): sample or staff
            executor_id (str): Code executor id
            source_code (str): Source code
            problem_name (str): ORA problem display name

        Returns:
            dict: output object with format like follows:
                {
                    'run_type': 'sample',
                    'total_tests': 0,
                    'correct': 0,
                    'incorrect': 0,
                    'output': OrderedDict(),
                    'error': None,
                }
        """
        xblock_id = self.get_xblock_id()
        usage_key = xblock_id.split('@')[-1]

        test_case_files = []
        question_mapping = AssessmentQuestionXblockMapping.objects.filter(usage_key=usage_key).first()

        if question_mapping:
            question = question_mapping.question
            test_case_files = self.read_test_cases_from_db(question, run_type)
        else:
            test_case_files = self.read_test_cases_from_file(problem_name, run_type)

        code_executor = CodeExecutorFactory.get_code_executor(
            executor_id,
            source_code=source_code,
            files=[files['input_file'] for files in test_case_files],
        )
        output = {
            'run_type': run_type,
            'total_tests': len(test_case_files),
            'correct': 0,
            'incorrect': 0,
            'output': OrderedDict(),
            'error': None,
        }
        # for server_shell paths start with / e.g. "/grader_data/..."
        # for epicbox paths are relative to home e.g. "grader_data/..."
        get_file_path = (
            lambda path: path.lstrip(os.sep)
            if self.executor == CodeExecutorOption.Epicbox.value
            else path
        )
        with code_executor:
            for case_file in test_case_files:
                if self.is_code_input_from_file:
                    execution_results = code_executor.run_input_from_file(
                        get_file_path(case_file['input_file']['name']),
                    )
                else:
                    execution_results = code_executor.run_input(
                        input=case_file['input_file']['content'].decode('utf-8'),
                    )

                formatted_results = self._executor_output_to_response_format(execution_results)
                run_output = self.compare_outputs(
                    formatted_results['output'],
                    case_file['expected_output_file']['name'],
                    problem_name,
                )

                if run_output['correct']:
                    output['correct'] += 1
                else:
                    output['incorrect'] += 1

                expected_output = run_output['tests'][0][1]
                actual_output = run_output['tests'][0][2]
                test_input = case_file['input_file']['content'].decode('utf-8')
                case_number = case_file['case_number']
                output['output'][case_number] = {
                    'test_input': test_input,
                    'actual_output': actual_output,
                    'expected_output': expected_output,
                    'correct': run_output['correct'],
                }

                input_file_name = case_file['input_file']['name']
                output_file_name = case_file['expected_output_file']['name']

                if question_mapping and os.path.isfile(input_file_name):
                    os.remove(input_file_name)
                if question_mapping and os.path.isfile(output_file_name):
                    os.remove(output_file_name)

        return output

    def run_design_code(self, executor_id, source_code):
        output = {
            'is_design_problem': True,
            'run_type': 'sample',
            'output': None,
            'error': None,
        }
        input_file_name = 'input.txt'
        code_executor = CodeExecutorFactory.get_code_executor(
            executor_id, source_code, files=[{'name': input_file_name, 'content': b''}]
        )

        if self.is_code_input_from_file and self.executor == CodeExecutorOption.ServerShell.value:
            input_file = TemporaryFile('r')
            input_file_name = input_file.name

        with code_executor:
            if self.is_code_input_from_file:
                execution_results = code_executor.run_input_from_file(input_file_name)
            else:
                execution_results = code_executor.run_input('')

            response = self._executor_output_to_response_format(execution_results)
            output = {
                **output,
                **response,
            }

        if self.is_code_input_from_file and self.executor == CodeExecutorOption.ServerShell.value:
            input_file.close()

        return output

    @classmethod
    def get_test_case_count(cls, problem_name, run_type):
        """
        Return the test case count of a given run type for a problem.

        Returns:
            Count of the test cases or None
        """
        test_cases = glob.glob(
            '{}{}/{}/*'.format(cls.__SECRET_DATA_DIR__, problem_name, run_type)
        )
        return len(test_cases) if test_cases else None

    def respond_with_error(self, message):
        """
        returns error response with message
        """
        return {'correct': False, 'score': 0, 'errors': [message], 'tests': []}

    def compare_outputs(self, actual_output, expected_output_file, problem_name):
        """
        compares actual and expected output line by line after stripping
        any whitespaces at the ends. Raises Exception if outputs do not match
        otherwise returns response of correct answer
        Args:
            actual_output(str): output of learner code
            expected_output_file(str): file name containing expected output of test case
            problem_name(str)
        """
        if not is_design_problem(problem_name):
            expected_output = open(expected_output_file, 'r').read().rstrip()
            actual_output = actual_output.rstrip()

            expected_output_splited = expected_output.split('\n')
            actual_output_splited = actual_output.split('\n')

            if actual_output_splited != expected_output_splited:
                return {
                    'correct': False,
                    'score': 0,
                    'errors': [],
                    'tests': [[False, expected_output, actual_output]],
                }
            else:
                return {
                    'correct': True,
                    'score': 1,
                    'errors': [],
                    'tests': [[True, expected_output, actual_output]],
                }
        else:
            return {
                'correct': True,
                'score': 1,
                'errors': [],
                'tests': [[True, "", actual_output.strip()]],
            }

    def process_execution_error(self, error):
        """
        Helper method to process and extract the execution error
        """
        try:
            output_error = error[0]
        except IndexError:
            output_error = error
        return truncate_error_output(output_error)

    def grade_response(self, data, problem_name, add_staff_output=False):
        """
        Grade the response with per file test case feature.
        """
        data.update({'problem_name': problem_name})

        output = self.grade(data, add_staff_cases=add_staff_output)

        sample_output = output[0]
        if add_staff_output:
            # If staff output is required, send the original result as it is.
            return output
        return sample_output
