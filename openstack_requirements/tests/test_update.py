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

import fixtures
import testtools
from testtools import matchers

from openstack_requirements.tests import common
from openstack_requirements import update


class UpdateTest(testtools.TestCase):

    def setUp(self):
        super(UpdateTest, self).setUp()
        self.global_env = self.useFixture(common.GlobalRequirements())

    def test_requirements(self):
        # This is testing our test input data. Perhaps remove? (lifeless)
        reqs = common._file_to_list(self.global_env.req_file)
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)

    def test_project(self):
        self.project = self.useFixture(common.project_fixture)
        update.main(['--source', self.global_env.root, self.project.root])
        reqs = common._file_to_list(self.project.req_file)
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_requirements_header(self):
        _REQS_HEADER = [
            '# The order of packages is significant, because pip processes '
            'them in the order',
            '# of appearance. Changing the order has an impact on the overall '
            'integration',
            '# process, which may cause wedges in the gate later.',
        ]
        self.project = self.useFixture(common.project_fixture)
        update.main(['--source', self.global_env.root, self.project.root])
        reqs = common._file_to_list(self.project.req_file)
        self.assertEqual(_REQS_HEADER, reqs[:3])

    def test_project_with_oslo(self):
        self.oslo_project = self.useFixture(common.oslo_fixture)
        update.main(
            ['--source', self.global_env.root, self.oslo_project.root])
        reqs = common._file_to_list(self.oslo_project.req_file)
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)

    def test_test_project(self):
        self.project = self.useFixture(common.project_fixture)
        update.main(['--source', self.global_env.root, self.project.root])
        reqs = common._file_to_list(self.project.test_req_file)
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        self.project = self.useFixture(common.project_fixture)
        update.main(['--source', self.global_env.root, self.project.root])
        setup_contents = common._file_to_list(self.project.setup_file)
        self.assertIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
                      " - DO NOT EDIT", setup_contents)

    def test_no_install_setup(self):
        self.oslo_project = self.useFixture(common.oslo_fixture)
        update.main(
            ['--source', self.global_env.root, self.oslo_project.root])
        setup_contents = common._file_to_list(self.oslo_project.setup_file)
        self.assertNotIn(
            "# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
            " - DO NOT EDIT", setup_contents)

    # These are tests which don't need to run the project update in advance
    def test_requirement_not_in_global(self):
        self.bad_project = self.useFixture(common.bad_project_fixture)
        with testtools.ExpectedException(Exception):
            update.main(
                ['--source', self.global_env.root, self.bad_project.root])

    def test_requirement_not_in_global_non_fatal(self):
        self.useFixture(
            fixtures.EnvironmentVariable("NON_STANDARD_REQS", "1"))
        self.bad_project = self.useFixture(common.bad_project_fixture)
        update.main(['--source', self.global_env.root, self.bad_project.root])

    def test_requirement_soft_update(self):
        self.bad_project = self.useFixture(common.bad_project_fixture)
        update.main([
            '-s', '--source', self.global_env.root, self.bad_project.root])
        reqs = common._file_to_list(self.bad_project.req_file)
        self.assertIn("thisisnotarealdepedency", reqs)

    # testing output
    def test_non_verbose_output(self):
        capture = StringIO.StringIO()
        self.project = self.useFixture(common.project_fixture)
        update.main(
            ['--source', self.global_env.root, self.project.root], capture)
        expected = ('Version change for: greenlet, sqlalchemy, eventlet, pastedeploy, routes, webob, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
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

    def test_verbose_output(self):
        capture = StringIO.StringIO()
        self.project = self.useFixture(common.project_fixture)
        update.main(
            ['--source', self.global_env.root, '-v', self.project.root],
            capture)
        expected = ("""Syncing %(project)s/requirements.txt
Version change for: greenlet, sqlalchemy, eventlet, pastedeploy, routes, webob, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n"""  # noqa
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
""") % dict(project=self.project.root)
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
                ['--source', '/dev/null', '/dev/zero'],
                _worker=check_params)

    def test_suffix(self):
        def check_params(
                root, source, suffix, softupdate, hacking, stdout, verbose,
                non_std_reqs):
            self.expectThat(suffix, matchers.Equals('global'))

        update.main(['-o', 'global', '/dev/zero'], _worker=check_params)
