#!/usr/bin/env python
"""
Determines the number of pylint violations (note that this includes both warnings and errors).
If larger than the supplied threshold, emits a status of 1 indicating failure.
"""

import re
import sys


USAGE = u"{} VIOLATIONS_FILE VIOLATIONS_THRESHOLD"


def count_pylint_violations(report_file):
    """
    Parses a pylint report line-by-line, and determins the number of pylint violations.

    Taken from https://github.com/edx/edx-platform/blob/master/pavelib/quality.py.
    """
    num_violations = 0
    # An example string:
    # common/lib/xmodule/xmodule/tests/test_conditional.py:21: [C0111(missing-docstring), DummySystem] Missing docstring
    # More examples can be found in the unit tests for this method
    pylint_pattern = re.compile(r".(\d+):\ \[(\D\d+.+\]).")

    for line in report_file:
        violation_list_for_line = pylint_pattern.split(line)
        # If the string is parsed into four parts, then we've found a violation. Example of split parts:
        # test file, line number, violation name, violation details
        if len(violation_list_for_line) == 4:
            num_violations += 1

    return num_violations


def main():
    """
    Main entry point for the script.
    """
    if len(sys.argv) < 3:
        print USAGE.format(sys.argv[0])
        sys.exit(1)

    try:
        with open(sys.argv[1]) as violations:
            num_violations = count_pylint_violations(violations)
            max_violations = sys.argv[2]
            print "Found {} pylint violations, threshold is {}".format(num_violations, max_violations)
            if num_violations > int(max_violations):
                violations.seek(0)
                for line in violations:
                    print line
                print "NUMBER OF PYLINT VIOLATIONS ({}) EXCEEDED THRESHOLD {}".format(num_violations, max_violations)
                sys.exit(1)
    except IOError as ex:
        print u"Could not open pylint violations file: {}".format(sys.argv[1])
        print(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
