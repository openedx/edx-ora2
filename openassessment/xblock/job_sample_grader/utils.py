"""
Holds utility functions related to code_grader module.
"""


OOP_PROBLEM_NAMES = ["design-problem-1", "design-problem-2", "design-problem-3"]


def is_design_problem(problem_name):
    """
    Temporary helper method to check if a coding problem is a design problem.
    """
    return problem_name in OOP_PROBLEM_NAMES


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


def truncate_error_output(output):
    """
    Truncate error output to last 150 lines if it is very long.
    """
    if len(output.split('\n')) > 150:
        actual_output = output.split("\n")[-150:]
        actual_output.append("... Extra output Trimmed.")
        return "\n".join(actual_output)
    return output
