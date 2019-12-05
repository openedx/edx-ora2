import subprocess
import time
import re
import os
import shutil


class TestGrader:
    # __SECRET_DATA_DIR__ = "secret_data/"
    # __TMP_DATA_DIR__ = "tmp_data/"
    __TMP_DATA_DIR__ = os.path.dirname(__file__) + "/tmp_data/"
    __SECRET_DATA_DIR__ = os.path.dirname(__file__) + "/secret_data/"

    def grade(self, response):
        problem_name = response['problem_name']
        source_code = response['submission'][0]
        code_file_name = "auto_generated_code_file_" + str(int(time.time()))
        if not os.path.exists(TestGrader.__TMP_DATA_DIR__ + code_file_name):
            os.mkdir(TestGrader.__TMP_DATA_DIR__ + code_file_name)

        code_file_path = TestGrader.__TMP_DATA_DIR__ + code_file_name + "/" + code_file_name

        try:
            lang, student_response = self.detect_code_language(source_code, code_file_name)
            full_code_file_name = '{0}.{1}'.format(code_file_path, lang)
            self.write_code_file(source_code, full_code_file_name)
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

        shutil.rmtree(TestGrader.__TMP_DATA_DIR__ + "/" + code_file_name)

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
                'javac -cp {0} {1}'.format(TestGrader.SECRET_DATA_DIR + "json-simple-1.1.1.jar", code_full_file_name),
                compiling=True)
            output = self.run_as_subprocess(
                'java -cp {0} {1}{2}'.format(
                    TestGrader.TMP_DATA_DIR + code_file_name + ":" + TestGrader.SECRET_DATA_DIR + "json-simple-1.1.1.jar",
                    code_file_name, input_file),
                running_code=True, timeout=timeout
            )

        elif lang == 'cpp':
            self.run_as_subprocess('g++ ' + code_full_file_name + ' -o ' + code_file_path, compiling=True)
            output = self.run_as_subprocess('./' + code_file_path + " " + input_file, running_code=True, timeout=timeout)

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
        # else:
        #     raise Exception('Language can only be C++, Java or Python.')
        else:
            lang = "py"
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

        if problem_name not in ["call-center"]:
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


if __name__ == '__main__':
    response = {
        u'submission': [u"from math import floor, sqrt\n\n\nclass Node:\n    \"\"\"\n    Representation of a tree's single node\n    \"\"\"\n\n    def __init__(self, value):\n        self.value = value\n        self.children = []\n    \n    def add_child(self, child):\n        self.children.append(child)\n    \n    def __repr__(self):\n        return \"%s %s\" % (self.value, self.children)\n\n\nclass Tree:\n\n    def __init__(self):\n\n        self.root = None\n        self.prime_nodes_count = 0\n    \n    def set_root(self, node):\n        self.root = node\n    \n    def update_prime_node_count(self):\n        '''\n        Traverse tree to update the prime node count if a node\n        has prime number of children.\n        '''\n        queue = []\n        queue.append(self.root)\n        while(len(queue)>0):\n            current_node = queue.pop(0)\n            for each in current_node.children:\n                queue.append(each)\n            if current_node.children:\n                if is_prime(len(current_node.children)):\n                    self.prime_nodes_count+=1\n    \n    def is_supreme(self, threshold):\n        if self.prime_nodes_count >= threshold:\n            return \"SUPREME\"\n        else:\n            return \"NORMAL\"\n        \n\ndef is_prime(number):\n    prime = True\n    if number==1:\n        return False\n    for j in range(2, floor(sqrt(number))+1):\n        if number%j==0:\n            prime = False\n            break\n    return prime\n    \n\ndef create_tree_from_input(data_string):\n    tree = Tree()\n    stack = []\n    node = None\n    for idx,data in enumerate(data_string):\n        if data == '(':\n            continue\n        elif data == ')' or data==',':\n            stack.pop()\n        else:\n            node = Node(data)\n            if stack != []:\n                stack[len(stack)-1].children.append(node)\n            stack.append(node)\n    tree.set_root(stack.pop(0))\n    return tree\n                \nif __name__=='__main__':\n    inp_file = open('secret_data/tree-sample.in', 'r')\n    test_cases = int(inp_file.readline())\n    for count in range(1, test_cases+1):\n        threshold = int(inp_file.readline())\n        data_string = inp_file.readline().strip()\n        tree = create_tree_from_input(data_string)\n        tree.update_prime_node_count()\n        print(\"CASE # {}: {}\".format(count, tree.is_supreme(threshold)))"],
        u'problem_name': 'tree'
    }
    output = TestGrader().grade(response)

    print(output)

