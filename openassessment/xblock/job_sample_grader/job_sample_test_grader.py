import subprocess
import time
import re
import os
import shutil
import uuid

from openassessment.xblock.utils import OOP_PROBLEM_NAMES


class TestGrader:

    __SECRET_DATA_DIR__ = "/grader_data/"
    __TMP_DATA_DIR__ = os.path.dirname(__file__) + "/tmp_data/"

    def grade(self, response):
        problem_name = response['problem_name']
        source_code = response['submission'][0]
        code_file_name = "auto_generated_code_file_" + str(uuid.uuid4())
        if not os.path.exists(TestGrader.__TMP_DATA_DIR__ + code_file_name):
            os.mkdir(TestGrader.__TMP_DATA_DIR__ + code_file_name)

        code_file_path = TestGrader.__TMP_DATA_DIR__ + code_file_name + "/" + code_file_name

        try:
            lang, student_response = self.detect_code_language(source_code, code_file_name)
            full_code_file_name = '{0}.{1}'.format(code_file_path, lang)
            self.write_code_file(student_response, full_code_file_name)
        except Exception as exc:
            return self.respond_with_error(exc.message)

        sample_input_file_argument = ' {0}{1}-sample.in'.format(self.__SECRET_DATA_DIR__, problem_name)
        sample_expected_output_file = '{0}{1}-sample.out'.format(self.__SECRET_DATA_DIR__, problem_name)
        input_file_argument = ' {0}{1}.in'.format(self.__SECRET_DATA_DIR__, problem_name)
        expected_output_file = '{0}{1}.out'.format(self.__SECRET_DATA_DIR__, problem_name)

        sample_test_case_result = self.run_test_cases(lang, code_file_name, full_code_file_name,
                                                      code_file_path, sample_input_file_argument,
                                                      sample_expected_output_file, 60, problem_name)
        secret_test_case_result = self.run_test_cases(lang, code_file_name, full_code_file_name,
                                                      code_file_path, input_file_argument,
                                                      expected_output_file, 60, problem_name)

        if sample_test_case_result["tests"]:
            sample_test_case_result["tests"][0].append("sample")
        if secret_test_case_result["tests"]:
            secret_test_case_result["tests"][0].append("staff")
            if sample_test_case_result["tests"]:
                sample_test_case_result["tests"].append(secret_test_case_result["tests"][0])

        shutil.rmtree(TestGrader.__TMP_DATA_DIR__ + code_file_name)

        return sample_test_case_result

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
        if error and compiling:
            raise Exception(error)
        elif error and running_code and 'Killed' in error:
            raise Exception('Time limit exceeded.')
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

    def execute_code(self, lang, code_file_name, code_full_file_name, code_file_path, input_file, timeout):
        """
        compiles the code, runs the code for python, java and c++ and returns output of the code
        """
        if lang == 'py':
            output = self.run_as_subprocess('python3 ' + code_full_file_name + input_file, running_code=True,
                                       timeout=timeout)

        elif lang == 'java':
            self.run_as_subprocess(
                'javac -cp {0} {1}'.format(TestGrader.__SECRET_DATA_DIR__ + "json-simple-1.1.1.jar", code_full_file_name),
                compiling=True)
            output = self.run_as_subprocess(
                'java -cp {0} {1}{2}'.format(
                    TestGrader.__TMP_DATA_DIR__ + code_file_name + ":" + TestGrader.__SECRET_DATA_DIR__ + "json-simple-1.1.1.jar",
                    code_file_name, input_file),
                running_code=True, timeout=timeout
            )

        elif lang == 'cpp':
            compiled_file_full_name_with_path = code_full_file_name + '.o'
            if not compiled_file_full_name_with_path.startswith('/'):
                compiled_file_full_name_with_path = '/' + compiled_file_full_name_with_path
            self.run_as_subprocess('g++ ' + code_full_file_name + ' -o ' + compiled_file_full_name_with_path, compiling=True)
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

        if len(actual_output.split('\n')) > 150:
            actual_output = actual_output.split("\n")[:149]
            actual_output.append("... Too much output. Extra output Trimmed.")
            actual_output = "\n".join(actual_output)

        if problem_name not in OOP_PROBLEM_NAMES:
            expected_output = open(expected_output_file, 'r').read().strip()
            actual_output = actual_output.strip()

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

    def run_test_cases(self, lang, code_file_name, full_code_file_name, code_file_path, input_file_argument,
                       expected_output_file, timeout, problem_name):
        # Run Sample Test Case
        try:
            output = self.execute_code(lang, code_file_name, full_code_file_name, code_file_path, input_file_argument,
                                  timeout)
            result = self.compare_outputs(output, expected_output_file, problem_name)
            return result
        except Exception as e:
            return self.respond_with_error(e.message)
