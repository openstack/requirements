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

import six
import sys
import textwrap
from unittest import mock

import fixtures
import testscenarios
import testtools
from testtools import matchers

from openstack_requirements.cmds import update
from openstack_requirements import project
from openstack_requirements import requirement
from openstack_requirements.tests import common


load_tests = testscenarios.load_tests_apply_scenarios


class SmokeTest(testtools.TestCase):

    def test_project(self):
        global_env = self.useFixture(common.GlobalRequirements())
        global_reqs = common._file_to_list(global_env.req_file)
        # This is testing our test input data. Perhaps remove? (lifeless)
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", global_reqs)
        # And test the end to end call of update.py, UI and all.
        self.project = self.useFixture(common.project_fixture)
        capture = six.StringIO()
        update.main(['--source', global_env.root, self.project.root], capture)
        reqs = common._file_to_list(self.project.req_file)
        # ensure various updates take
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy<=0.7.99,>=0.7", reqs)
        expected = ('Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
                    """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=1.0.17     ->   SQLAlchemy<=0.7.99,>=0.7
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb<1.3,>=1.2.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    python-swiftclient>=1.2,<4     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema!=1.4.0,<2,>=1.0.0
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.21.0                   ->   mox3>=0.7.0
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
            if type(action) is project.File:
                self.assertNotEqual(action.filename, 'setup.py')

    # These are tests which don't need to run the project update in advance
    def test_requirement_not_in_global(self):
        actions = update._process_project(
            common.bad_project, common.global_reqs, None, None, None, False)
        errors = [a for a in actions if type(a) is project.Error]
        msg = u"'thisisnotarealdependency' is not in global-requirements.txt"
        self.assertIn(msg, errors[0].message)

    def test_requirement_in_blacklist(self):
        actions = update._process_project(
            common.bad_project, common.global_reqs, None, None, None, False,
            blacklist={'thisisnotarealdependency': None})
        errors = [a for a in actions if type(a) is project.Error]
        self.assertEqual([], errors)

    def test_requirement_not_in_global_non_fatal(self):
        reqs = common.project_file(
            self.fail, common.bad_project, 'requirements.txt',
            non_std_reqs=True)
        self.assertNotIn("thisisnotarealdependency", reqs)

    def test_requirement_soft_update(self):
        reqs = common.project_file(
            self.fail, common.bad_project, 'requirements.txt',
            softupdate=True)
        self.assertIn("thisisnotarealdependency", reqs)

    # testing output
    def test_non_verbose_output(self):
        actions = update._process_project(
            common.project_project, common.global_reqs, None, None, None,
            False)
        capture = six.StringIO()
        project.write(
            common.project_project, actions, capture, False, True)
        expected = ('Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
                    """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=1.0.17     ->   SQLAlchemy<=0.7.99,>=0.7
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb<1.3,>=1.2.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    python-swiftclient>=1.2,<4     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema!=1.4.0,<2,>=1.0.0
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.21.0                   ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
""") % dict(project=common.project_project['root'])
        self.assertEqual(expected, capture.getvalue())

    def test_verbose_output(self):
        actions = update._process_project(
            common.project_project, common.global_reqs, None, None, None,
            False)
        capture = six.StringIO()
        project.write(
            common.project_project, actions, capture, True, True)
        expected = ("""Syncing %(project)s/requirements.txt
Version change for: greenlet, SQLAlchemy, eventlet, PasteDeploy, routes, WebOb, wsgiref, boto, kombu, python-swiftclient, lxml, jsonschema, python-keystoneclient\n"""  # noqa
                    """Updated %(project)s/requirements.txt:
    greenlet>=0.3.1                ->   greenlet>=0.3.2
    SQLAlchemy>=0.7.8,<=1.0.17     ->   SQLAlchemy<=0.7.99,>=0.7
    eventlet>=0.9.12               ->   eventlet>=0.12.0
    PasteDeploy                    ->   PasteDeploy>=1.5.0
    routes                         ->   Routes>=1.12.3
    WebOb>=1.2                     ->   WebOb<1.3,>=1.2.3
    wsgiref                        ->   wsgiref>=0.1.2
    boto                           ->   boto>=2.4.0
    kombu>2.4.7                    ->   kombu>=2.4.8
    python-swiftclient>=1.2,<4     ->   python-swiftclient>=1.2
    lxml                           ->   lxml>=2.3
    jsonschema                     ->   jsonschema!=1.4.0,<2,>=1.0.0
    python-keystoneclient>=0.2.0   ->   python-keystoneclient>=0.4.1
Syncing %(project)s/test-requirements.txt
Version change for: mox, mox3, testrepository, testtools
Updated %(project)s/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.21.0                   ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
Syncing setup.py
""") % dict(project=common.project_project['root'])
        self.assertEqual(expected, capture.getvalue())


class TestMain(testtools.TestCase):

    @mock.patch('os.path.isdir', return_value=True)
    def test_smoke(self, mock_isdir):
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
        self.expectThat(mock_isdir.called, matchers.Equals(True))

    @mock.patch('os.path.isdir', return_value=True)
    def test_suffix(self, mock_isdir):
        def check_params(
                root, source, suffix, softupdate, hacking, stdout, verbose,
                non_std_reqs):
            self.expectThat(suffix, matchers.Equals('global'))

        update.main(['-o', 'global', '/dev/zero'], _worker=check_params)
        self.expectThat(mock_isdir.called, matchers.Equals(True))

    def test_isdirectory(self):
        def never_called(
                root, source, suffix, softupdate, hacking, stdout, verbose,
                non_std_reqs):
            self.expectThat(False, matchers.Equals(True),
                            message=("update.main() should riase an "
                                     "exception before getting here"))

        with testtools.ExpectedException(Exception,
                                         "/dev/zero is not a directory"):
            update.main(['/dev/zero'], _worker=never_called)


class TestSyncRequirementsFile(testtools.TestCase):

    def test_multiple_lines_in_global_one_in_project(self):
        global_content = textwrap.dedent("""\
            foo<2;python_version=='2.7'
            foo>1;python_version!='2.7'
            """)
        project_content = textwrap.dedent("""\
            foo
            """)
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement(
                'foo', '', '<2', "python_version=='2.7'", ''),
            requirement.Requirement(
                'foo', '', '>1', "python_version!='2.7'", '')]),
            reqs)
        self.assertEqual(project.StdOut(
            "    foo                            "
            "->   foo<2;python_version=='2.7'\n"), actions[2])
        self.assertEqual(project.StdOut(
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
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement(
                'foo', '', '<2', "python_version=='2.7'", ''),
            requirement.Requirement(
                'foo', '', '>1', "python_version!='2.7'", ''),
            requirement.Requirement(
                '', '', '', '', "# mumbo gumbo")]),
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
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement(
                'foo', '', '<2', "python_version=='2.7'", ''),
            requirement.Requirement(
                'foo', '', '>1', "python_version!='2.7'", ''),
            requirement.Requirement(
                '', '', '', '', "# mumbo gumbo")]),
            reqs)
        self.assertEqual(project.StdOut(
            "    foo<1.8;python_version=='2.7'  ->   "
            "foo<2;python_version=='2.7'\n"), actions[2])
        self.assertEqual(project.StdOut(
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
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement(
                'foo', '', '<2', "python_version=='2.7'", ''),
            requirement.Requirement(
                'foo', '', '>1', "python_version!='2.7'", '')]),
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
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement('foo', '', '>1', "", '')]),
            reqs)
        self.assertEqual(project.StdOut(
            "    foo<2;python_version=='2.7'    ->   foo>1\n"), actions[2])
        self.assertEqual(project.StdOut(
            "    foo>1;python_version!='2.7'    ->   \n"), actions[3])
        self.assertThat(actions, matchers.HasLength(4))

    def test_unparseable_line(self):
        global_content = textwrap.dedent("""\
            foo
            """)
        project_content = textwrap.dedent("""\
            foo
            -e https://git.openstack.org/openstack/neutron.git#egg=neutron
            """)
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        n = '-e https://git.openstack.org/openstack/neutron.git#egg=neutron'
        self.assertEqual(requirement.Requirements([
            requirement.Requirement('foo', '', '', '', ''),
            requirement.Requirement('', '', '', '', n)]),
            reqs)

    def test_extras_kept(self):
        global_content = textwrap.dedent("""\
            oslo.db>1.4.1
            """)
        project_content = textwrap.dedent("""\
            oslo.db[fixture,mysql]>1.3
            """)
        global_reqs = requirement.parse(global_content)
        project_reqs = list(requirement.to_reqs(project_content))
        actions, reqs = update._sync_requirements_file(
            global_reqs, project_reqs, 'f', False, False, False)
        self.assertEqual(requirement.Requirements([
            requirement.Requirement(
                'oslo.db', '', '>1.4.1', '', '', ['fixture', 'mysql'])]),
            reqs)
        self.assertThat(actions, matchers.HasLength(3))
        self.assertEqual(project.StdOut(
            "    oslo.db[fixture,mysql]>1.3     ->   "
            "oslo.db[fixture,mysql]>1.4.1\n"), actions[2])


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
        proj = {}
        proj['root'] = '/dev/null'
        proj['requirements'] = {}
        proj['setup.cfg'] = setup_cfg
        global_reqs = requirement.parse(global_content)
        actions = update._copy_requires(
            u'', False, False, proj, global_reqs, False)
        self.assertEqual([
            project.Verbose('Syncing extra [opt]'),
            project.Verbose('Syncing extra [test]'),
            project.File('setup.cfg', setup_cfg)], actions)
