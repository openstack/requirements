# Copyright 2013 IBM Corp.
#
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

from __future__ import print_function

import io
import StringIO
import sys
import textwrap

import fixtures
import parsley
import pkg_resources
import testscenarios
import testtools
from testtools import matchers

from openstack_requirements.tests import common
from openstack_requirements import update


load_tests = testscenarios.load_tests_apply_scenarios


class SmokeTest(testtools.TestCase):

    def test_project(self):
        global_env = self.useFixture(common.GlobalRequirements())
        global_reqs = common._file_to_list(global_env.req_file)
        # This is testing our test input data. Perhaps remove? (lifeless)
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", global_reqs)
        # And test the end to end call of update.py, UI and all.
        self.project = self.useFixture(common.project_fixture)
        capture = StringIO.StringIO()
        update.main(['--source', global_env.root, self.project.root], capture)
        reqs = common._file_to_list(self.project.req_file)
        # ensure various updates take
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy<=0.7.99,>=0.7", reqs)
        expected = ('Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
            """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=0.7.99     ->   SQLAlchemy>=0.7,<=0.7.99
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb>=1.2.3,<1.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    pycrypto>=2.1.0alpha1          ->   pycrypto>=2.6
    python-swiftclient>=1.2,<2     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema>=1.0.0,!=1.4.0,<2
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.7.3                    ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
""") % dict(project=self.project.root)
        self.assertEqual(expected, capture.getvalue())


class UpdateTest(testtools.TestCase):

    def test_project(self):
        reqs = common.project_file(
            self.fail, common.project_project, 'requirements.txt')
        # ensure various updates take
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy<=0.7.99,>=0.7", reqs)

    def test_requirements_header(self):
        _REQS_HEADER = [
            '# The order of packages is significant, because pip processes '
            'them in the order',
            '# of appearance. Changing the order has an impact on the overall '
            'integration',
            '# process, which may cause wedges in the gate later.',
        ]
        reqs = common.project_file(
            self.fail, common.project_project, 'requirements.txt')
        self.assertEqual(_REQS_HEADER, reqs[:3])

    def test_project_with_oslo(self):
        reqs = common.project_file(
            self.fail, common.oslo_project, 'requirements.txt')
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)

    def test_test_project(self):
        reqs = common.project_file(
            self.fail, common.project_project, 'test-requirements.txt')
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        setup_contents = common.project_file(
            self.fail, common.project_project, 'setup.py', suffix='global')
        self.assertIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
                      " - DO NOT EDIT", setup_contents)

    def test_no_install_setup(self):
        actions = update._process_project(
            common.oslo_project, common.global_reqs, None, None, None,
            False)
        for action in actions:
            if type(action) is update.File:
                self.assertNotEqual(action.filename, 'setup.py')

    # These are tests which don't need to run the project update in advance
    def test_requirement_not_in_global(self):
        with testtools.ExpectedException(Exception):
            update._process_project(
                common.bad_project, common.global_reqs, None, None, None,
                False)

    def test_requirement_not_in_global_non_fatal(self):
        reqs = common.project_file(
            self.fail, common.bad_project, 'requirements.txt',
            non_std_reqs=True)
        self.assertNotIn("thisisnotarealdependency", reqs)

    def test_requirement_soft_update(self):
        reqs = common.project_file(
            self.fail, common.bad_project, 'requirements.txt',
            softupdate=True)
        self.assertIn("thisisnotarealdepedency", reqs)

    # testing output
    def test_non_verbose_output(self):
        actions = update._process_project(
            common.project_project, common.global_reqs, None, None, None,
            False)
        capture = StringIO.StringIO()
        update._write_project(
            common.project_project, actions, capture, False, True)
        expected = ('Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
            """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=0.7.99     ->   SQLAlchemy>=0.7,<=0.7.99
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb>=1.2.3,<1.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    pycrypto>=2.1.0alpha1          ->   pycrypto>=2.6
    python-swiftclient>=1.2,<2     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema>=1.0.0,!=1.4.0,<2
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.7.3                    ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
""") % dict(project=common.project_project['root'])
        self.assertEqual(expected, capture.getvalue())

    def test_verbose_output(self):
        actions = update._process_project(
            common.project_project, common.global_reqs, None, None, None,
            False)
        capture = StringIO.StringIO()
        update._write_project(
            common.project_project, actions, capture, True, True)
        expected = ("""Syncing %(project)s/requirements.txt
Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n"""  # noqa
            """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=0.7.99     ->   SQLAlchemy>=0.7,<=0.7.99
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb>=1.2.3,<1.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    pycrypto>=2.1.0alpha1          ->   pycrypto>=2.6
    python-swiftclient>=1.2,<2     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema>=1.0.0,!=1.4.0,<2
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Syncing %(project)s/test-requirements.txt
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.7.3                    ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
Syncing setup.py
""") % dict(project=common.project_project['root'])
        self.assertEqual(expected, capture.getvalue())


class TestReadProject(testtools.TestCase):

    def test_pbr(self):
        root = self.useFixture(common.pbr_fixture).root
        project = update._read_project(root)
        self.expectThat(project['root'], matchers.Equals(root))
        setup_py = open(root + '/setup.py', 'rt').read()
        self.expectThat(project['setup.py'], matchers.Equals(setup_py))
        setup_cfg = open(root + '/setup.cfg', 'rt').read()
        self.expectThat(project['setup.cfg'], matchers.Equals(setup_cfg))
        self.expectThat(
            project['requirements'],
            matchers.KeysEqual('requirements.txt', 'test-requirements.txt'))

    def test_no_setup_py(self):
        root = self.useFixture(fixtures.TempDir()).path
        project = update._read_project(root)
        self.expectThat(
            project, matchers.Equals({'root': root, 'requirements': {}}))


class TestWriteProject(testtools.TestCase):

    def test_smoke(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        project = {'root': root}
        actions = [
            update.File('foo', '123\n'),
            update.File('bar', '456\n'),
            update.Verbose(u'fred')]
        update._write_project(project, actions, stdout, True)
        foo = open(root + '/foo', 'rt').read()
        self.expectThat(foo, matchers.Equals('123\n'))
        bar = open(root + '/bar', 'rt').read()
        self.expectThat(bar, matchers.Equals('456\n'))
        self.expectThat(stdout.getvalue(), matchers.Equals('fred\n'))

    def test_non_verbose(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        project = {'root': root}
        actions = [update.Verbose(u'fred')]
        update._write_project(project, actions, stdout, False)
        self.expectThat(stdout.getvalue(), matchers.Equals(''))

    def test_bad_action(self):
        root = self.useFixture(fixtures.TempDir()).path
        stdout = io.StringIO()
        project = {'root': root}
        actions = [('foo', 'bar')]
        with testtools.ExpectedException(Exception):
            update._write_project(project, actions, stdout, True)

    def test_stdout(self):
        stdout = io.StringIO()
        root = self.useFixture(fixtures.TempDir()).path
        project = {'root': root}
        actions = [update.StdOut(u'fred\n')]
        update._write_project(project, actions, stdout, True)
        self.expectThat(stdout.getvalue(), matchers.Equals('fred\n'))


class TestMain(testtools.TestCase):

    def test_smoke(self):
        def check_params(
                root, source, suffix, softupdate, hacking, stdout, verbose,
                non_std_reqs):
            self.expectThat(root, matchers.Equals('/dev/zero'))
            self.expectThat(source, matchers.Equals('/dev/null'))
            self.expectThat(suffix, matchers.Equals(''))
            self.expectThat(softupdate, matchers.Equals(None))
            self.expectThat(hacking, matchers.Equals(None))
            self.expectThat(stdout, matchers.Equals(sys.stdout))
            self.expectThat(verbose, matchers.Equals(None))
            self.expectThat(non_std_reqs, matchers.Equals(True))

        with fixtures.EnvironmentVariable('NON_STANDARD_REQS', '1'):
            update.main(
                ['--source', '/dev/null', '/dev/zero'], _worker=check_params)

    def test_suffix(self):
        def check_params(
                root, source, suffix, softupdate, hacking, stdout, verbose,
                non_std_reqs):
            self.expectThat(suffix, matchers.Equals('global'))

        update.main(['-o', 'global', '/dev/zero'], _worker=check_params)


class TestParseRequirement(testtools.TestCase):

    scenarios = [
        ('package', dict(
         line='swift',
         req=update.Requirement('swift', '', '', ''))),
        ('specifier', dict(
         line='alembic>=0.4.1',
         req=update.Requirement('alembic', '>=0.4.1', '', ''))),
        ('specifiers', dict(
         line='alembic>=0.4.1,!=1.1.8',
         req=update.Requirement('alembic', '!=1.1.8,>=0.4.1', '', ''))),
        ('comment-only', dict(
         line='# foo',
         req=update.Requirement('', '', '', '# foo'))),
        ('comment', dict(
         line='Pint>=0.5  # BSD',
         req=update.Requirement('Pint', '>=0.5', '', '# BSD'))),
        ('comment-with-semicolon', dict(
         line='Pint>=0.5  # BSD;fred',
         req=update.Requirement('Pint', '>=0.5', '', '# BSD;fred'))),
        ('case', dict(
         line='Babel>=1.3',
         req=update.Requirement('Babel', '>=1.3', '', ''))),
        ('markers', dict(
         line="pywin32;sys_platform=='win32'",
         req=update.Requirement('pywin32', '', "sys_platform=='win32'", ''))),
        ('markers-with-comment', dict(
         line="Sphinx<=1.2; python_version=='2.7'# Sadface",
         req=update.Requirement('Sphinx', '<=1.2', "python_version=='2.7'",
                                '# Sadface')))]

    def test_parse(self):
        parsed = update._parse_requirement(self.line)
        self.assertEqual(self.req, parsed)


class TestParseRequirementFailures(testtools.TestCase):

    scenarios = [
        ('url', dict(line='http://tarballs.openstack.org/oslo.config/'
                          'oslo.config-1.2.0a3.tar.gz#egg=oslo.config')),
        ('-e', dict(line='-e git+https://foo.com#egg=foo')),
        ('-f', dict(line='-f http://tarballs.openstack.org/'))]

    def test_does_not_parse(self):
        with testtools.ExpectedException(pkg_resources.RequirementParseError):
            update._parse_requirement(self.line)


class TestSyncRequirementsFile(testtools.TestCase):

    def test_multiple_lines_in_global_one_in_project(self):
        global_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        project_content = textwrap.dedent("""\
            foo
            """)
        global_reqs = update._parse_reqs(global_content)
        project_reqs = list(update._content_to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(update.Requirements([
            update.Requirement('foo', '<2', "python_version=='2.7'", ''),
            update.Requirement('foo', '>1', "python_version!='2.7'", '')]),
            reqs)
        self.assertEqual(update.StdOut(
            "    foo                            "
            "->   foo<2;python_version=='2.7'\n"), actions[2])
        self.assertEqual(update.StdOut(
            "                                   "
            "->   foo>1;python_version!='2.7'\n"), actions[3])
        self.assertThat(actions, matchers.HasLength(4))

    def test_multiple_lines_separated_in_project_nochange(self):
        global_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        project_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            # mumbo gumbo
            foo>1;python_version!='2.7'
            """)
        global_reqs = update._parse_reqs(global_content)
        project_reqs = list(update._content_to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(update.Requirements([
            update.Requirement('foo', '<2', "python_version=='2.7'", ''),
            update.Requirement('foo', '>1', "python_version!='2.7'", ''),
            update.Requirement('', '', '', "# mumbo gumbo")]),
            reqs)
        self.assertThat(actions, matchers.HasLength(0))

    def test_multiple_lines_separated_in_project(self):
        global_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        project_content = textwrap.dedent("""\
            foo<1.8;python_version=='2.7'
            # mumbo gumbo
            foo>0.9;python_version!='2.7'
            """)
        global_reqs = update._parse_reqs(global_content)
        project_reqs = list(update._content_to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(update.Requirements([
            update.Requirement('foo', '<2', "python_version=='2.7'", ''),
            update.Requirement('foo', '>1', "python_version!='2.7'", ''),
            update.Requirement('', '', '', "# mumbo gumbo")]),
            reqs)
        self.assertEqual(update.StdOut(
            "    foo<1.8;python_version=='2.7'  ->   "
            "foo<2;python_version=='2.7'\n"), actions[2])
        self.assertEqual(update.StdOut(
            "    foo>0.9;python_version!='2.7'  ->   "
            "foo>1;python_version!='2.7'\n"), actions[3])
        self.assertThat(actions, matchers.HasLength(4))

    def test_multiple_lines_nochange(self):
        global_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        project_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        global_reqs = update._parse_reqs(global_content)
        project_reqs = list(update._content_to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(update.Requirements([
            update.Requirement('foo', '<2', "python_version=='2.7'", ''),
            update.Requirement('foo', '>1', "python_version!='2.7'", '')]),
            reqs)
        self.assertThat(actions, matchers.HasLength(0))

    def test_single_global_multiple_in_project(self):
        global_content = textwrap.dedent("""\
            foo>1
            """)
        project_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        global_reqs = update._parse_reqs(global_content)
        project_reqs = list(update._content_to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(update.Requirements([
            update.Requirement('foo', '>1', "", '')]),
            reqs)
        self.assertEqual(update.StdOut(
            "    foo<2;python_version=='2.7'    ->   foo>1\n"), actions[2])
        self.assertEqual(update.StdOut(
            "    foo>1;python_version!='2.7'    ->   \n"), actions[3])
        self.assertThat(actions, matchers.HasLength(4))


class TestReqsToContent(testtools.TestCase):

    def test_smoke(self):
        reqs = update._reqs_to_content(update.Requirements(
            [update.Requirement(
             'foo', '<=1', "python_version=='2.7'", '# BSD')]),
            marker_sep='!')
        self.assertEqual(
            ''.join(update._REQS_HEADER
                    + ["foo<=1!python_version=='2.7' # BSD\n"]),
            reqs)


class TestProjectExtras(testtools.TestCase):

    def test_smoke(self):
        project = {'setup.cfg': textwrap.dedent(u"""
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
        self.assertEqual(expected, update._project_extras(project))

    def test_none(self):
        project = {'setup.cfg': u"[metadata]\n"}
        self.assertEqual({}, update._project_extras(project))


class TestExtras(testtools.TestCase):

    def test_none(self):
        old_content = textwrap.dedent(u"""
            [metadata]
            # something something
            name = fred

            [entry_points]
            console_scripts =
                foo = bar:quux
            """)
        ini = update.extras_compiled(old_content).ini()
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
        ini = update.extras_compiled(old_content).ini()
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
            update.extras_compiled(old_content).ini()

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
            update.Comment('# comment1\n'),
            update.Extra('a', '\nb\nc\n'),
            update.Comment('# comment2\n'),
            update.Comment('# comment3\n'),
            update.Extra('d', '\ne\n'),
            update.Comment('# comment4\n')]
        ini = update.extras_compiled(old_content).ini()
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
        merged = update._merge_setup_cfg(old_content, {})
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
        blank = update.Requirement('', '', '', '')
        r1 = update.Requirement('b', '>=1', "python_version=='2.7'", '')
        r2 = update.Requirement('d', '', '', '# BSD')
        reqs = {
            'a': update.Requirements([blank, r1]),
            'c': update.Requirements([blank, r2])}
        merged = update._merge_setup_cfg(old_content, reqs)
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


class TestCopyRequires(testtools.TestCase):

    def test_extras_no_change(self):
        global_content = textwrap.dedent(u"""\
            foo<2;python_version=='2.7' # BSD
            foo>1;python_version!='2.7'
            freddy
            """)
        setup_cfg = textwrap.dedent(u"""\
            [metadata]
            name = openstack.requirements

            [extras]
            test =
              foo<2:python_version=='2.7' # BSD
              foo>1:python_version!='2.7'
            opt =
              freddy
            """)
        project = {}
        project['root'] = '/dev/null'
        project['requirements'] = {}
        project['setup.cfg'] = setup_cfg
        global_reqs = update._parse_reqs(global_content)
        actions = update._copy_requires(
            u'', False, False, project, global_reqs, False)
        self.assertEqual([
            update.Verbose('Syncing extra [opt]'),
            update.Verbose('Syncing extra [test]'),
            update.File('setup.cfg', setup_cfg)], actions)
