import glob
import logging
import os
import re
import shutil
import subprocess
import uuid

from collections import OrderedDict

from openassessment.xblock.utils import OOP_PROBLEM_NAMES


logger = logging.getLogger(__name__)


class TestGrader:

    __SECRET_DATA_DIR__ = "/grader_data/"
    __TMP_DATA_DIR__ = os.path.dirname(__file__) + "/tmp_data/"

    def grade(self, response, add_staff_cases=False):
        problem_name = response['problem_name']
        source_code = response['submission'][0]
        code_file_name = "auto_generated_code_file_" + str(uuid.uuid4()).replace('-', '')
        if not os.path.exists(TestGrader.__TMP_DATA_DIR__ + code_file_name):
            os.mkdir(TestGrader.__TMP_DATA_DIR__ + code_file_name)

        code_file_path = TestGrader.__TMP_DATA_DIR__ + code_file_name + "/" + code_file_name

        try:
            lang, student_response = self.detect_code_language(source_code, code_file_name)
            full_code_file_name = '{0}.{1}'.format(code_file_path, lang)
            self.write_code_file(student_response, full_code_file_name)
        except UnicodeEncodeError as e:
            return self.response_with_error_v2("{} - {} : {}".format(
                e.start, e.end, e.reason
            ))
        except Exception as exc:
            return self.response_with_error_v2(exc.message)

        output = []
        sample_result = self.run_code('sample', lang, code_file_name, full_code_file_name, problem_name)
        output.append(sample_result)
        if add_staff_cases:
            staff_result = self.run_code('staff', lang, code_file_name, full_code_file_name, problem_name)
            output.append(staff_result)

        shutil.rmtree(TestGrader.__TMP_DATA_DIR__ + code_file_name)

        return output

    def response_with_error_v2(self, error):
        """
        To make the incorrect language error compatible with per file test
        case run compatible.
        """
        return [self.get_error_response('sample', error)]

    @staticmethod
    def get_error_response(run_type, error):
        """
        Create a sample error response for a given run and the error to be displayed.
        """
        return {
            'run_type': run_type,
            'total_tests': 0,
            'correct': 0,
            'incorrect': 0,
            'output': None,
            'error': [error]
        }

    def run_code(self, run_type, lang, code_file_name, full_code_file_name, problem_name):

        test_cases = glob.glob("{}{}/{}/*".format(self.__SECRET_DATA_DIR__, problem_name, run_type))

        # Sort the test cases based on the test number
        if test_cases:
            test_cases = sorted(test_cases, key=lambda test_case: int(test_case.split('/')[-1]))

        output = {
            'run_type': run_type,
            'total_tests': len(test_cases),
            'correct': 0,
            'incorrect': 0,
            'output': OrderedDict(),
            'error': None
        }
        for case in test_cases:
            case_number = int(case.split('/')[-1])
            input_file = "{}/input.in".format(case)
            expected_output_file = "{}/output.out".format(case)
            run_output = self.run_test_cases(
                lang, code_file_name,
                full_code_file_name,
                input_file,
                expected_output_file,
                timeout=5,
                problem_name=problem_name
            )
            # If execution faced error, stop processing
            if run_output['errors']:
                output['error'] = run_output['errors']
                break
            if run_output['correct']:
                output['correct'] += 1
            else:
                output['incorrect'] += 1
            expected_output = run_output['tests'][0][1]
            actual_output = run_output['tests'][0][2]
            test_input = open(input_file, 'r').read()
            output['output'][case_number] = {
                'test_input': test_input,
                'actual_output': actual_output,
                'expected_output': expected_output,
                'correct': run_output['correct']
            }

        return output

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
        error = error.decode('utf-8')
        if error and compiling:
            raise Exception(error)
        elif error and running_code and 'Killed' in error:
            return u'Time limit exceeded.'
        elif error and running_code:
            raise Exception(error)

        return output.decode('utf-8')

    def respond_with_error(self, message):
        """
        returns error response with message
        """
        return {
            'correct': False,
            'score': 0,
            'errors': [message],
            'tests': []
        }

    def execute_code(self, lang, code_file_name, code_full_file_name, input_file, timeout=10):
        """
        compiles the code, runs the code for python, java and c++ and returns output of the code
        """
        if lang == 'py':
            output = self.run_as_subprocess('python3 {} {}'.format(code_full_file_name, input_file), running_code=True,
                                       timeout=timeout)

        elif lang == 'java':
            self.run_as_subprocess(
                'javac -cp {0} {1}'.format(TestGrader.__SECRET_DATA_DIR__ + "json-simple-1.1.1.jar", code_full_file_name),
                compiling=True)
            output = self.run_as_subprocess(
                'java -cp {0} {1} {2}'.format(
                    TestGrader.__TMP_DATA_DIR__ + code_file_name + ":" + TestGrader.__SECRET_DATA_DIR__ + "json-simple-1.1.1.jar",
                    code_file_name, input_file),
                running_code=True, timeout=timeout
            )

        elif lang == 'cpp':
            compiled_file_full_name_with_path = code_full_file_name + '.o'
            if not compiled_file_full_name_with_path.startswith('/'):
                compiled_file_full_name_with_path = '/' + compiled_file_full_name_with_path
            self.run_as_subprocess('g++ ' + code_full_file_name + ' -o ' + compiled_file_full_name_with_path + ' -lcurl -ljsoncpp', compiling=True)
            output = self.run_as_subprocess(compiled_file_full_name_with_path + " " + input_file, running_code=True, timeout=timeout)

        else:
            raise Exception
        return output

    def detect_code_language(self, source_code, code_file_name):
        """
        detects language using guesslang module and raises exception if
        language is not in one of these. JAVA, C++, PYTHON. for java
        replaces the public class name with file name to execute the code.
        LIMIT: Expects only one public class in Java solution
        """
        output = self.run_as_subprocess("echo '" + source_code + "' | guesslang")

        if 'Python' not in output and 'Java' not in output and 'C++' not in output:
            output = source_code.split("\n")[0]

        if 'Python' in output:
            lang = "py"
        elif 'Java' in output:
            lang = 'java'
            source_code = re.sub(
                'public class (.*) {', 'public class {0} {{'.format(code_file_name), source_code
            )
        elif 'C++' in output:
            lang = 'cpp'
        else:
            raise Exception('Language can only be C++, Java or Python.')
        # else:
        #     lang = "py"
        return lang, source_code

    def write_code_file(self, source_code, full_code_file_name):
        """
        accepts code and file name to where the code will be written.
        """
        f = open(full_code_file_name, 'w')
        f.write(source_code)
        f.close()

    def compare_outputs(self, actual_output, expected_output_file, problem_name):
        """
        compares actual and expected output line by line after stripping
        any whitespaces at the ends. Raises Exception if outputs do not match
        otherwise returns response of correct answer
        """

        if problem_name not in OOP_PROBLEM_NAMES:
            expected_output = open(expected_output_file, 'r').read().rstrip()
            actual_output = actual_output.rstrip()

            expected_output_splited = expected_output.split('\n')
            actual_output_splited = actual_output.split('\n')

            if actual_output_splited != expected_output_splited:
                return {
                    'correct': False,
                    'score': 0,
                    'errors': [],
                    'tests': [[False, expected_output, actual_output]]
                }
            else:
                return {
                    'correct': True,
                    'score': 1,
                    'errors': [],
                    'tests': [[True, expected_output, actual_output]]
                }
        else:
            return {
                'correct': True,
                'score': 1,
                'errors': [],
                'tests': [[True, "", actual_output.strip()]]
            }

    def run_test_cases(self, lang, code_file_name, full_code_file_name, input_file_argument,
                       expected_output_file, timeout=10, problem_name=''):
        # Run Sample Test Case
        try:
            output = self.execute_code(lang, code_file_name, full_code_file_name, input_file_argument, timeout)
            result = self.compare_outputs(output, expected_output_file, problem_name)
            return result
        except Exception as e:
            return self.respond_with_error(e.message)


if __name__ == '__main__':
    grader = TestGrader()
    inp_file = os.path.dirname(__file__) + '/secret_data/tree.py'
    data = {
        'problem_name': 'tree',
        'submission': [
            open(inp_file, 'r').read()
        ]
    }
    output = grader.grade(data)[0]
    print(output['output'][1]['correct'])
