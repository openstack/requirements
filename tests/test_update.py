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

import os
import os.path
import shutil
import StringIO

import fixtures
import testtools

import update


def _file_to_list(fname):
    with open(fname) as f:
        content = list(map(lambda x: x.rstrip(), f.readlines()))
        print(content)
        return content


class UpdateTest(testtools.TestCase):

    def _init_env(self):
        self.project_dir = os.path.join(self.dir, "project")
        self.bad_project_dir = os.path.join(self.dir, "bad_project")
        self.oslo_dir = os.path.join(self.dir, "project_with_oslo")

        self.req_file = os.path.join(self.dir, "global-requirements.txt")
        self.proj_file = os.path.join(self.project_dir, "requirements.txt")
        self.oslo_file = os.path.join(self.oslo_dir, "requirements.txt")
        self.bad_proj_file = os.path.join(self.bad_project_dir,
                                          "requirements.txt")
        self.proj_test_file = os.path.join(self.project_dir,
                                           "test-requirements.txt")
        self.setup_file = os.path.join(self.project_dir, "setup.py")
        self.old_setup_file = os.path.join(self.oslo_dir, "setup.py")
        self.bad_setup_file = os.path.join(self.bad_project_dir, "setup.py")
        self.setup_cfg_file = os.path.join(self.project_dir, "setup.cfg")
        self.bad_setup_cfg_file = os.path.join(self.bad_project_dir,
                                               "setup.cfg")
        self.oslo_setup_cfg_file = os.path.join(self.oslo_dir, "setup.cfg")
        os.mkdir(self.project_dir)
        os.mkdir(self.oslo_dir)
        os.mkdir(self.bad_project_dir)

        shutil.copy("tests/files/gr-base.txt", self.req_file)
        shutil.copy("tests/files/project-with-oslo-tar.txt", self.oslo_file)
        shutil.copy("tests/files/project.txt", self.proj_file)
        shutil.copy("tests/files/project-with-bad-requirement.txt",
                    self.bad_proj_file)
        shutil.copy("tests/files/test-project.txt", self.proj_test_file)
        shutil.copy("tests/files/setup.py", self.setup_file)
        shutil.copy("tests/files/setup.py", self.bad_setup_file)
        shutil.copy("tests/files/old-setup.py", self.old_setup_file)
        shutil.copy("tests/files/setup.cfg", self.setup_cfg_file)
        shutil.copy("tests/files/setup.cfg", self.bad_setup_cfg_file)
        shutil.copy("tests/files/setup.cfg", self.oslo_setup_cfg_file)
        shutil.copy("update.py", os.path.join(self.dir, "update.py"))

    def _run_update(self):
        # now go call update and see what happens
        update.main(['project'])
        update.main(['project_with_oslo'])

    def setUp(self):
        super(UpdateTest, self).setUp()
        self.dir = self.useFixture(fixtures.TempDir()).path
        self._init_env()
        # for convenience put us in the directory with the update.py
        self.addCleanup(os.chdir, os.path.abspath(os.curdir))
        os.chdir(self.dir)

    def test_requirements(self):
        self._run_update()
        reqs = _file_to_list(self.req_file)
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)

    def test_project(self):
        self._run_update()
        reqs = _file_to_list(self.proj_file)
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_requirements_header(self):
        self._run_update()
        _REQS_HEADER = [
            '# The order of packages is significant, because pip processes '
            'them in the order',
            '# of appearance. Changing the order has an impact on the overall '
            'integration',
            '# process, which may cause wedges in the gate later.',
        ]
        reqs = _file_to_list(self.proj_file)
        self.assertEqual(_REQS_HEADER, reqs[:3])

    def test_project_with_oslo(self):
        self._run_update()
        reqs = _file_to_list(self.oslo_file)
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)

    def test_test_project(self):
        self._run_update()
        reqs = _file_to_list(self.proj_test_file)
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        self._run_update()
        setup_contents = _file_to_list(self.setup_file)
        self.assertIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
                      " - DO NOT EDIT", setup_contents)

    def test_no_install_setup(self):
        self._run_update()
        setup_contents = _file_to_list(self.old_setup_file)
        self.assertNotIn(
            "# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
            " - DO NOT EDIT", setup_contents)

    # These are tests which don't need to run the project update in advance
    def test_requirment_not_in_global(self):
        with testtools.ExpectedException(Exception):
            update.main(['bad_project'])

    def test_requirment_not_in_global_non_fatal(self):
        self.useFixture(
            fixtures.EnvironmentVariable("NON_STANDARD_REQS", "1"))
        update.main(["bad_project"])

    def test_requirement_soft_update(self):
        update.main(["-s", "bad_project"])
        reqs = _file_to_list(self.bad_proj_file)
        self.assertIn("thisisnotarealdepedency", reqs)

    # testing output
    def test_non_verbose_output(self):
        capture = StringIO.StringIO()
        update.main(['project'], capture)
        expected = 'Version change for: greenlet, sqlalchemy, eventlet, pastedeploy, routes, webob, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n'  # noqa
        expected += """Updated project/requirements.txt:
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
Updated project/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.7.3                    ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
"""
        self.assertEqual(expected, capture.getvalue())

    def test_verbose_output(self):
        capture = StringIO.StringIO()
        update.main(['-v', 'project'], capture)
        expected = """Syncing project/requirements.txt
Version change for: greenlet, sqlalchemy, eventlet, pastedeploy, routes, webob, wsgiref, boto, kombu, pycrypto, python-swiftclient, lxml, jsonschema, python-keystoneclient\n"""  # noqa
        expected += """Updated project/requirements.txt:
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
Syncing project/test-requirements.txt
Version change for: mox, mox3, testrepository, testtools
Updated project/test-requirements.txt:
    mox==0.5.3                     ->   mox>=0.5.3
    mox3==0.7.3                    ->   mox3>=0.7.0
    testrepository>=0.0.13         ->   testrepository>=0.0.17
    testtools>=0.9.27              ->   testtools>=0.9.32
Syncing setup.py
"""
        self.assertEqual(expected, capture.getvalue())
