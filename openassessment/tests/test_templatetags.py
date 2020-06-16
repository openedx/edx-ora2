""" Tests for custom django template tags. """


import unittest

import ddt
import six

from django.template import Context, Template


@ddt.ddt
class OAExtrasTests(unittest.TestCase):
    """ Tests for custom django template tags oa_extras. """

    template = Template(
        u"{% load oa_extras %}"
        u"{{ text|link_and_linebreak }}"
    )

    @ddt.data(
        ("", ""),
        ('check this https://dummy-url.com', 'https://dummy-url.com'),
        ('Visit this URL http://dummy-url.com', 'http://dummy-url.com'),
        ('dummy-text http://dummy-url.org', 'http://dummy-url.org'),
        ('dummy-url.com dummy-text', 'dummy-url.com')
    )
    @ddt.unpack
    def test_link_and_linebreak(self, text, link_text):
        rendered_template = self.template.render(Context({'text': text}))
        self.assertIn(link_text, rendered_template)
        if text:
            six.assertRegex(
                self,
                rendered_template,
                r'<a.*target="_blank".*>{link_text}</a>'.format(link_text=link_text),
            )

    @ddt.data(
        ("hello <script></script>", "script"),
        ("http://dummy-url.com <applet></applet>", "applet"),
        ("<iframe></iframe>", "iframe"),
        ("<link></link>", "link"),
    )
    @ddt.unpack
    def test_html_tags(self, text, tag):
        rendered_template = self.template.render(Context({'text': text}))
        escaped_tag = "&lt;{tag}&gt;".format(tag=tag)
        self.assertIn(escaped_tag, rendered_template)
