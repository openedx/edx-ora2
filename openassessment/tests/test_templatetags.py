import ddt
from django.template import Context, Template
import unittest


@ddt.ddt
class OAExtrasTests(unittest.TestCase):

    template = Template(
        "{% load oa_extras %}"
        "{{ text|link_and_linebreak }}"
    )

    @ddt.data(
        ("", ""),
        ('Check this https://dummy-url.com for details', 'https://dummy-url.com'),
        ('http://dummy-url.com', 'http://dummy-url.com'),
        ('http://dummy-url.org', 'http://dummy-url.org'),
        ('http://dummy-url.ag', 'http://dummy-url.ag'),
        ('dummy-url.com', 'dummy-url.com')
    )
    @ddt.unpack
    def test_link_and_linebreak(self, text, link_text):
        rendered_template = self.template.render(Context({'text': text}))
        self.assertIn(link_text, rendered_template)
        if text:
            self.assertRegexpMatches(
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
