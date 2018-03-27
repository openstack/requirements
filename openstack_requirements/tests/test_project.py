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

import io
import textwrap

import fixtures
import parsley
import testscenarios
import testtools
from testtools import matchers

from openstack_requirements import project
from openstack_requirements import requirement
from openstack_requirements.tests import common


load_tests = testscenarios.load_tests_apply_scenarios


class TestReadProject(testtools.TestCase):

    def test_pbr(self):
        root = self.useFixture(common.pbr_fixture).root
        proj = project.read(root)
        self.expectThat(proj['root'], matchers.Equals(root))
        setup_py = open(root + '/setup.py', 'rt').read()
        self.expectThat(proj['setup.py'], matchers.Equals(setup_py))
        setup_cfg = open(root + '/setup.cfg', 'rt').read()
        self.expectThat(proj['setup.cfg'], matchers.Equals(setup_cfg))
        self.expectThat(
            proj['requirements'],
            matchers.KeysEqual('requirements.txt', 'test-requirements.txt'))

    def test_no_setup_py(self):
        root = self.useFixture(fixtures.TempDir()).path
        proj = project.read(root)
        self.expectThat(
            proj, matchers.Equals({'root': root, 'requirements': {},
                                   'lower-constraints.txt': None}))


class TestProjectExtras(testtools.TestCase):

    def test_smoke(self):
        proj = {'setup.cfg': textwrap.dedent(u"""
            [extras]
            1 =
              foo
            2 =
              foo # fred
              bar
            """)}
        expected = {
            '1': '\nfoo',
            '2': '\nfoo # fred\nbar'
        }
        self.assertEqual(expected, project.extras(proj))

    def test_none(self):
        proj = {'setup.cfg': u"[metadata]\n"}
        self.assertEqual({}, project.extras(proj))

    def test_no_setup_cfg(self):
        proj = {}
        self.assertEqual({}, project.extras(proj))


class TestExtrasParsing(testtools.TestCase):

    def test_none(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        ini = project._extras_compiled(old_content).ini()
        self.assertEqual(ini, (old_content, None, ''))

    def test_no_eol(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [entry_points]
            console_scripts =
                foo = bar:quux""")
        expected1 = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [entry_points]
            console_scripts =
            """)
        suffix = '    foo = bar:quux'
        ini = project._extras_compiled(old_content).ini()
        self.assertEqual(ini, (expected1, None, suffix))

    def test_two_extras_raises(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [extras]
            a = b
            [extras]
            b = c

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        with testtools.ExpectedException(parsley.ParseError):
            project._extras_compiled(old_content).ini()

    def test_extras(self):
        # We get an AST for extras we can use to preserve comments.
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [extras]
            # comment1
            a =
             b
             c
            # comment2
            # comment3
            d =
             e
            # comment4

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        prefix = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            """)
        suffix = textwrap.dedent(u"""\
            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        extras = [
            project._Comment('# comment1\n'),
            project._Extra('a', '\nb\nc\n'),
            project._Comment('# comment2\n'),
            project._Comment('# comment3\n'),
            project._Extra('d', '\ne\n'),
            project._Comment('# comment4\n')]
        ini = project._extras_compiled(old_content).ini()
        self.assertEqual(ini, (prefix, extras, suffix))


class TestMergeSetupCfg(testtools.TestCase):

    def test_merge_none(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        merged = project.merge_setup_cfg(old_content, {})
        self.assertEqual(old_content, merged)

    def test_merge_extras(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            name = fred

            [extras]
            # Comment
            a =
             b
            # comment
            c =
             d

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        blank = requirement.Requirement('', '', '', '', '')
        r1 = requirement.Requirement(
            'b', '', '>=1', "python_version=='2.7'", '')
        r2 = requirement.Requirement('d', '', '', '', '# BSD')
        reqs = {
            'a': requirement.Requirements([blank, r1]),
            'c': requirement.Requirements([blank, r2])}
        merged = project.merge_setup_cfg(old_content, reqs)
        expected = textwrap.dedent(u"""
            [metadata]
            name = fred

            [extras]
            # Comment
            a =
              b>=1:python_version=='2.7'
            # comment
            c =
              d # BSD

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        self.assertEqual(expected, merged)


class TestWriteProject(testtools.TestCase):

    def test_smoke(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        proj = {'root': root}
        actions = [
            project.File('foo', '123\n'),
            project.File('bar', '456\n'),
            project.Verbose(u'fred')]
        project.write(proj, actions, stdout, True)
        foo = open(root + '/foo', 'rt').read()
        self.expectThat(foo, matchers.Equals('123\n'))
        bar = open(root + '/bar', 'rt').read()
        self.expectThat(bar, matchers.Equals('456\n'))
        self.expectThat(stdout.getvalue(), matchers.Equals('fred\n'))

    def test_non_verbose(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        proj = {'root': root}
        actions = [project.Verbose(u'fred')]
        project.write(proj, actions, stdout, False)
        self.expectThat(stdout.getvalue(), matchers.Equals(''))

    def test_bad_action(self):
        root = self.useFixture(fixtures.TempDir()).path
        stdout = io.StringIO()
        proj = {'root': root}
        actions = [('foo', 'bar')]
        with testtools.ExpectedException(Exception):
            project.write(proj, actions, stdout, True)

    def test_stdout(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        proj = {'root': root}
        actions = [project.StdOut(u'fred\n')]
        project.write(proj, actions, stdout, True)
        self.expectThat(stdout.getvalue(), matchers.Equals('fred\n'))

    def test_errors(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        proj = {'root': root}
        actions = [project.Error(u'fred')]
        with testtools.ExpectedException(Exception):
            project.write(proj, actions, stdout, True)
        self.expectThat(stdout.getvalue(), matchers.Equals('fred\n'))
