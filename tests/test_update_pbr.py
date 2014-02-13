# Copyright 2013 IBM Corp.
# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Based on test_update.py

from __future__ import print_function

import os
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


class UpdateTestPbr(testtools.TestCase):

    def setUp(self):
        super(UpdateTestPbr, self).setUp()
        self.dir = tempfile.mkdtemp()
        self.project_dir = os.path.join(self.dir, "project_pbr")

        self.req_file = os.path.join(self.dir, "global-requirements.txt")
        self.dev_req_file = os.path.join(self.dir, "dev-requirements.txt")
        self.proj_file = os.path.join(self.project_dir, "requirements.txt")
        self.proj_test_file = os.path.join(self.project_dir,
                                           "test-requirements.txt")
        self.setup_file = os.path.join(self.project_dir, "setup.py")
        self.setup_cfg_file = os.path.join(self.project_dir, "setup.cfg")
        os.mkdir(self.project_dir)

        shutil.copy("tests/files/gr-base.txt", self.req_file)
        shutil.copy("tests/files/dev-req.txt", self.dev_req_file)
        shutil.copy("tests/files/project.txt", self.proj_file)
        shutil.copy("tests/files/test-project.txt", self.proj_test_file)
        shutil.copy("tests/files/setup.py", self.setup_file)
        shutil.copy("tests/files/pbr_setup.cfg", self.setup_cfg_file)
        shutil.copy("update.py", os.path.join(self.dir, "update.py"))

        # now go call update and see what happens
        self.addCleanup(os.chdir, os.path.abspath(os.curdir))
        os.chdir(self.dir)
        subprocess.call([sys.executable, "update.py", "project_pbr"])

    def test_requirements(self):
        reqs = _file_to_list(self.req_file)
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)

    def test_project(self):
        reqs = _file_to_list(self.proj_file)
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_test_project(self):
        reqs = _file_to_list(self.proj_test_file)
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        setup_contents = _file_to_list(self.setup_file)
        self.assertNotIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS "
                         "REPO - DO NOT EDIT", setup_contents)
