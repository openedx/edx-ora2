"""
Base class for handler-level testing of the XBlock.
"""
import os.path
import json
from functools import wraps

from django.test import TestCase
from workbench.runtime import WorkbenchRuntime
import webob


def scenario(scenario_path, user_id=None):
    """
    Method decorator to load a scenario for a test case.
    Must be called on an `XBlockHandlerTestCase` subclass, or
    else it will have no effect.

    Args:
        scenario_path (str): Path to the scenario XML file.

    Kwargs:
        user_id (str or None): User ID to log in as, or None.

    Returns:
        The decorated method

    Example:

        @scenario('data/test_scenario.xml')
        def test_submit(self, xblock):
            response = self.request(xblock, 'submit', 'Test submission')
            self.assertTrue('Success' in response)
    """
    def _decorator(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):

            # Retrieve the object (self)
            # if this is a function, not a method, then do nothing.
            xblock = None
            if args:
                self = args[0]
                if isinstance(self, XBlockHandlerTestCase):

                    # Print a debug message
                    print "Loading scenario from {path}".format(path=scenario_path)

                    # Configure the runtime with our user id
                    self.set_user(user_id)

                    # Load the scenario
                    xblock = self.load_scenario(scenario_path)

                    # Pass the XBlock as the first argument to the decorated method (after `self`)
                    args = list(args)
                    args.insert(1, xblock)

            return func(*args, **kwargs)
        return _wrapped
    return _decorator


class XBlockHandlerTestCase(TestCase):
    """
    Load the XBlock in the workbench runtime to test its handler.
    """

    def setUp(self):
        """
        Create the runtime.
        """
        self.runtime = WorkbenchRuntime()

    def set_user(self, user_id):
        """
        Provide a user ID to the runtime.

        Args:
            user_id (str): a user ID.

        Returns:
            None
        """
        self.runtime.user_id = user_id

    def load_scenario(self, xml_path):
        """
        Load an XML definition of an XBlock and return the XBlock instance.

        Args:
            xml (string): Path to an XML definition of the XBlock, relative
                to the test module.

        Returns:
            XBlock
        """
        block_id = self.runtime.parse_xml_string(
            self.load_fixture_str(xml_path), self.runtime.id_generator
        )
        return self.runtime.get_block(block_id)

    def request(self, xblock, handler_name, content, response_format=None):
        """
        Make a request to an XBlock handler.

        Args:
            xblock (XBlock): The XBlock instance that should handle the request.
            handler_name (str): The name of the handler.
            content (unicode): Content of the request.

        Kwargs:
            response_format (None or str): Expected format of the response string.
                If `None`, return the raw response content; if 'json', parse the
                response as JSON and return the result.

        Raises:
            NotImplementedError: Response format not supported.

        Returns:
            Content of the response (mixed).
        """
        # Create a fake request
        request = webob.Request(dict())
        request.body = content

        # Send the request to the XBlock handler
        response = self.runtime.handle(xblock, handler_name, request)

        # Parse the response (if a format is specified)
        if response_format is None:
            return response.body
        elif response_format == 'json':
            return json.loads(response.body)
        else:
            raise NotImplementedError("Response format '{format}' not supported".format(response_format))

    @staticmethod
    def load_fixture_str(path):
        """
        Load data from a fixture file.

        Args:
            path (str): Path to the file.

        Returns:
            unicode: contents of the file.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, path)) as file_handle:
            return file_handle.read()
