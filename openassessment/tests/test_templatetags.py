import re
import ddt
from django.template import Context, Template
import unittest


@ddt.ddt
class OAExtrasTests(unittest.TestCase):

    @ddt.data(
        ("", ""),
        ('https://dummy-url.com', 'href="https://dummy-url.com"'),
        ('http://dummy-url.com', 'href="http://dummy-url.com"'),
        ('http://dummy-url.org', 'href="http://dummy-url.org"'),
        ('http://dummy-url.ag', 'href="http://dummy-url.ag"'),
        ('dummy-url.com', 'href="http://dummy-url.com"')
    )
    @ddt.unpack
    def test_link_and_linebreak(self, text, expected_text):
        template = Template(
            "{% load oa_extras %}"
            "{{ text|link_and_linebreak }}"
        )
        rendered_template = template.render(Context({'text': text}))
        self.assertIn(expected_text, rendered_template)
        if text:
            self.assertTrue(bool(
                re.search(
                    "<a.*target.*href.*{text}.*</a>".format(text=text),
                    rendered_template
                )
            ))
