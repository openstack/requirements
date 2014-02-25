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
import subprocess
import sys
import tempfile
import testtools


def _file_to_list(fname):
    with open(fname) as f:
        content = list(map(lambda x: x.rstrip(), f.readlines()))
        print(content)
        return content


class UpdateTestWithSuffix(testtools.TestCase):

    def setUp(self):
        super(UpdateTestWithSuffix, self).setUp()
        self.dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.dir, "project")
        self.oslo_dir = os.path.join(self.dir, "project_with_oslo")

        self.req_file = os.path.join(self.dir, "global-requirements.txt")
        self.dev_req_file = os.path.join(self.dir, "dev-requirements.txt")
        self.proj_file = os.path.join(self.project_dir, "requirements.txt")
        self.oslo_file = os.path.join(self.oslo_dir, "requirements.txt")
        self.proj_test_file = os.path.join(self.project_dir,
                                           "test-requirements.txt")
        self.setup_file = os.path.join(self.project_dir, "setup.py")
        self.old_setup_file = os.path.join(self.oslo_dir, "setup.py")
        self.setup_cfg_file = os.path.join(self.project_dir, "setup.cfg")
        self.oslo_setup_cfg_file = os.path.join(self.oslo_dir, "setup.cfg")
        os.mkdir(self.project_dir)
        os.mkdir(self.oslo_dir)

        shutil.copy("tests/files/gr-base.txt", self.req_file)
        shutil.copy("tests/files/dev-req.txt", self.dev_req_file)
        shutil.copy("tests/files/project-with-oslo-tar.txt", self.oslo_file)
        shutil.copy("tests/files/project.txt", self.proj_file)
        shutil.copy("tests/files/test-project.txt", self.proj_test_file)
        shutil.copy("tests/files/setup.py", self.setup_file)
        shutil.copy("tests/files/old-setup.py", self.old_setup_file)
        shutil.copy("tests/files/setup.cfg", self.setup_cfg_file)
        shutil.copy("tests/files/setup.cfg", self.oslo_setup_cfg_file)
        shutil.copy("update.py", os.path.join(self.dir, "update.py"))

        # now go call update and see what happens
        self.addCleanup(os.chdir, os.path.abspath(os.curdir))
        os.chdir(self.dir)
        subprocess.call([sys.executable, "update.py",
                         "-o", "global", "project"])
        subprocess.call([sys.executable, "update.py",
                         "-o", "global", "project_with_oslo"])

    def test_requirements(self):
        # this is the sanity check test
        reqs = _file_to_list(self.req_file)
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)

    def test_project(self):
        reqs = _file_to_list("%s.%s" % (self.proj_file, 'global'))
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_project_with_oslo(self):
        reqs = _file_to_list("%s.%s" % (self.oslo_file, 'global'))
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)
        self.assertIn("oslo.config>=1.2.0a3", reqs)
        self.assertNotIn("oslo.config>=1.1.0", reqs)

    def test_test_project(self):
        reqs = _file_to_list("%s.%s" % (self.proj_test_file, 'global'))
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        setup_contents = _file_to_list(self.setup_file)
        self.assertIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
                      " - DO NOT EDIT", setup_contents)

    def test_no_install_setup(self):
        setup_contents = _file_to_list(self.old_setup_file)
        self.assertNotIn(
            "# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
            " - DO NOT EDIT", setup_contents)
