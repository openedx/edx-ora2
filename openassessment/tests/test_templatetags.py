import ddt
from django.template import Context, Template
import unittest


@ddt.ddt
class OAExtrasTests(unittest.TestCase):

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
        template = Template(
            "{% load oa_extras %}"
            "{{ text|link_and_linebreak }}"
        )
        rendered_template = template.render(Context({'text': text}))
        self.assertIn(link_text, rendered_template)
        if text:
            self.assertRegexpMatches(
                rendered_template,
                r'<a.*target="_blank".*>{link_text}</a>'.format(link_text=link_text),
            )


    # def test_html_tags(self):
    #     template = Template(
    #         "{% load oa_extras %}"
    #         "{{ text|link_and_linebreak }}"
    #     )
    #     rendered_template = template.render(Context({'text': "hello http://dummy.com <script>alert('kkk')</script>"}))
    #     from nose.tools import set_trace; set_trace()
    #
