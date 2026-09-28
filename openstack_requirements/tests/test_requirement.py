#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import textwrap

import testtools

from openstack_requirements import requirement


class TestParseRequirement(testtools.TestCase):
    dist_scenarios = [
        (
            'package',
            'swift',
            requirement.Requirement('swift', '', '', '', ''),
            False,
        ),
        (
            'specifier',
            'alembic>=0.4.1',
            requirement.Requirement('alembic', '', '>=0.4.1', '', ''),
            False,
        ),
        (
            'specifiers',
            'alembic>=0.4.1,!=1.1.8',
            requirement.Requirement('alembic', '', '!=1.1.8,>=0.4.1', '', ''),
            False,
        ),
        (
            'comment-only',
            '# foo',
            requirement.Requirement('', '', '', '', '# foo'),
            False,
        ),
        (
            'comment',
            'Pint>=0.5  # BSD',
            requirement.Requirement('Pint', '', '>=0.5', '', '# BSD'),
            False,
        ),
        (
            'comment-with-semicolon',
            'Pint>=0.5  # BSD;fred',
            requirement.Requirement('Pint', '', '>=0.5', '', '# BSD;fred'),
            False,
        ),
        (
            'case',
            'Babel>=1.3',
            requirement.Requirement('Babel', '', '>=1.3', '', ''),
            False,
        ),
        (
            'markers',
            "pywin32;sys_platform=='win32'",
            requirement.Requirement(
                'pywin32', '', '', "sys_platform=='win32'", ''
            ),
            False,
        ),
        (
            'markers-with-comment',
            "Sphinx<=1.2; python_version=='2.7'# Sadface",
            requirement.Requirement(
                'Sphinx', '', '<=1.2', "python_version=='2.7'", '# Sadface'
            ),
            False,
        ),
    ]
    url_scenarios = [
        (
            'url',
            'file:///path/to/thing#egg=thing',
            requirement.Requirement(
                'thing', 'file:///path/to/thing', '', '', ''
            ),
            True,
        ),
        (
            'oslo-url',
            'file:///path/to/oslo.thing#egg=oslo.thing',
            requirement.Requirement(
                'oslo.thing', 'file:///path/to/oslo.thing', '', '', ''
            ),
            True,
        ),
        (
            'url-comment',
            'file:///path/to/thing#egg=thing # http://altpath#egg=boo',
            requirement.Requirement(
                'thing',
                'file:///path/to/thing',
                '',
                '',
                '# http://altpath#egg=boo',
            ),
            True,
        ),
        (
            'editable',
            '-e file:///path/to/bar#egg=bar',
            requirement.Requirement(
                'bar', '-e file:///path/to/bar', '', '', ''
            ),
            True,
        ),
        (
            'editable_vcs_git',
            '-e git+http://github.com/path/to/oslo.bar#egg=oslo.bar',
            requirement.Requirement(
                'oslo.bar',
                '-e git+http://github.com/path/to/oslo.bar',
                '',
                '',
                '',
            ),
            True,
        ),
        (
            'editable_vcs_git_ssh',
            '-e git+ssh://github.com/path/to/oslo.bar#egg=oslo.bar',
            requirement.Requirement(
                'oslo.bar',
                '-e git+ssh://github.com/path/to/oslo.bar',
                '',
                '',
                '',
            ),
            True,
        ),
    ]
    scenarios = dist_scenarios + url_scenarios

    def test_parse(self):
        for name, line, req, permit_urls in self.scenarios:
            with self.subTest(name):
                parsed = requirement.parse_line(line, permit_urls=permit_urls)
                self.assertEqual(req, parsed)


class TestParseRequirementFailures(testtools.TestCase):
    scenarios = [
        (
            'url',
            'http://tarballs.openstack.org/oslo.config/oslo.config-1.2.0a3.tar.gz#egg=oslo.config',
        ),
        ('-e', '-e git+https://foo.com#egg=foo'),
        ('-f', '-f http://tarballs.openstack.org/'),
    ]

    def test_does_not_parse(self):
        for name, line in self.scenarios:
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    requirement.parse_line(line)


class TestToContent(testtools.TestCase):
    def test_smoke(self):
        reqs = requirement.to_content(
            requirement.Requirements(
                [
                    requirement.Requirement(
                        'foo', '', '<=1', "python_version=='2.7'", '# BSD'
                    )
                ]
            ),
            marker_sep='!',
        )
        self.assertEqual("foo<=1!python_version=='2.7' # BSD\n", reqs)

    def test_location(self):
        reqs = requirement.to_content(
            requirement.Requirements(
                [
                    requirement.Requirement(
                        'foo',
                        'file://foo',
                        '',
                        "python_version=='2.7'",
                        '# BSD',
                    )
                ]
            )
        )
        self.assertEqual(
            "file://foo#egg=foo;python_version=='2.7' # BSD\n", reqs
        )


class TestToReqs(testtools.TestCase):
    def test_editable(self):
        line = '-e file:///foo#egg=foo'
        reqs = list(requirement.to_reqs(line, permit_urls=True))
        req = requirement.Requirement('foo', '-e file:///foo', '', '', '')
        self.assertEqual(reqs, [(req, line)])

    def test_urls(self):
        line = 'file:///foo#egg=foo'
        reqs = list(requirement.to_reqs(line, permit_urls=True))
        req = requirement.Requirement('foo', 'file:///foo', '', '', '')
        self.assertEqual(reqs, [(req, line)])

    def test_not_urls(self):
        self.assertRaises(
            ValueError, list, requirement.to_reqs('file:///foo#egg=foo')
        )

    def test_multiline(self):
        content = textwrap.dedent("""\
            oslo.config>=1.11.0     # Apache-2.0
            oslo.concurrency>=2.3.0 # Apache-2.0
            oslo.context>=0.2.0     # Apache-2.0
            """)
        reqs = requirement.parse(content)
        self.assertEqual(
            {'oslo-config', 'oslo-concurrency', 'oslo-context'},
            set(reqs.keys()),
        )

    def test_extras(self):
        content = textwrap.dedent("""\
            oslo.config>=1.11.0 # Apache-2.0
            oslo.concurrency[fixtures]>=1.11.0 # Apache-2.0
            oslo.db[fixtures,mysql]>=1.11.0 # Apache-2.0
            """)
        reqs = requirement.parse(content)
        self.assertEqual(
            {'oslo-config', 'oslo-concurrency', 'oslo-db'},
            set(reqs.keys()),
        )
        self.assertEqual(reqs['oslo-config'][0][0].extras, frozenset(()))
        self.assertEqual(
            reqs['oslo-concurrency'][0][0].extras, frozenset(('fixtures',))
        )
        self.assertEqual(
            reqs['oslo-db'][0][0].extras, frozenset(('fixtures', 'mysql'))
        )
        self.assertCountEqual(
            reqs, ['oslo-config', 'oslo-concurrency', 'oslo-db']
        )


class TestCanonicalName(testtools.TestCase):
    def test_underscores(self):
        self.assertEqual('foo-bar', requirement.canonical_name('Foo_bar'))


class TestToDict(testtools.TestCase):
    def test_canonicalises(self):
        req = requirement.Requirement('Foo_bar', '', '', '', '')
        self.assertEqual(
            {'foo-bar': [(req, '')]}, requirement.to_dict([(req, '')])
        )


class TestReqPolicy(testtools.TestCase):
    def test_requirements_policy_pass(self):
        content = textwrap.dedent("""\
            cffi!=1.1.2
            other
            """)
        reqs = requirement.parse(content)
        policy_check = [x for x in requirement.check_reqs_bounds_policy(reqs)]
        self.assertEqual(len(policy_check), 0)

    def test_requirements_policy_fail(self):
        content = textwrap.dedent("""\
            cffi>=1.1.1,!=1.1.0
            other>=1,>=2,!=1.1.0
            """)
        reqs = requirement.parse(content)
        self.assertEqual(
            [
                'Requirement cffi should not include a >= specifier',
                'Requirement other should not include a >= specifier',
            ],
            sorted([x for x in requirement.check_reqs_bounds_policy(reqs)]),
        )
