#!/usr/bin/env python
"""
Render Django templates.
Useful for generating fixtures for the JavaScript unit test suite.

Usage:
    python render_templates.py path/to/templates.json

where "templates.json" is a JSON file of the form:
    [
        {
            "template": "openassessmentblock/oa_base.html",
            "context": {
                "title": "Lorem",
                "question": "Ipsum?"
            },
            "output": "oa_base.html"
        },
        ...
    ]

The rendered templates are saved to "output" relative to the
templates.json file's directory.
"""
import sys
import os.path
import json
import re
import dateutil.parser
import pytz

# This is a bit of a hack to ensure that the root repo directory
# is in the front of the Python path, so Django can find the settings module.
sys.path.insert(1,os.path.dirname(os.path.dirname(__file__)))
import django
from django.template.context import Context
from django.template.loader import get_template


USAGE = u"{prog} TEMPLATE_DESC"


DATETIME_REGEX = re.compile("^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

django.setup()

def parse_dates(context):
    """
    Transform datetime strings into Python datetime objects.

    JSON does not provide a standard way to serialize datetime objects,
    but some of the templates expect that the context contains
    Python datetime objects.

    This (somewhat hacky) solution recursively searches the context
    for formatted datetime strings of the form "2014-01-02T12:34"
    and converts them to Python datetime objects with the timezone
    set to UTC.

    Args:
        context (JSON-serializable): The context (or part of the context)
            that will be passed to the template.  Dictionaries and lists
            will be recursively searched and transformed.

    Returns:
        JSON-serializable of the same type as the `context` argument.

    """
    if isinstance(context, dict):
        return {
            key: parse_dates(value)
            for key, value in context.iteritems()
        }
    elif isinstance(context, list):
        return [
            parse_dates(item)
            for item in context
        ]
    elif isinstance(context, basestring):
        if DATETIME_REGEX.match(context) is not None:
            return dateutil.parser.parse(context).replace(tzinfo=pytz.utc)

    return context


def render_templates(root_dir, template_json):
    """
    Create rendered templates.

    Args:
        root_dir (str): The directory in which to write the rendered templates.
        template_json (dict): Description of which templates to render.  Must be a list
            of dicts, each containing keys "template" (str), "context" (dict), and "output" (str).

    Returns:
        None

    """
    for template_dict in template_json:
        template = get_template(template_dict['template'])
        context = parse_dates(template_dict['context'])
        rendered = template.render(Context(context))
        output_path = os.path.join(root_dir, template_dict['output'])

        try:
            with open(output_path, 'w') as output_file:
                output_file.write(rendered.encode('utf-8'))
        except IOError:
            print "Could not write rendered template to file: {}".format(output_path)
            sys.exit(1)


def main():
    """
    Main entry point for the script.
    """
    if len(sys.argv) < 2:
        print USAGE.format(sys.argv[0])
        sys.exit(1)

    try:
        with open(sys.argv[1]) as template_json:
            root_dir = os.path.dirname(sys.argv[1])
            render_templates(root_dir, json.load(template_json))
    except IOError as ex:
        print u"Could not open template description file: {}".format(sys.argv[1])
        print(ex)
        sys.exit(1)
    except ValueError as ex:
        print u"Could not parse template description as JSON: {}".format(sys.argv[1])
        print(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
