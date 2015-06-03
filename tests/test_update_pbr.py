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

import testtools

from tests import common
import update


class UpdateTestPbr(testtools.TestCase):

    def setUp(self):
        super(UpdateTestPbr, self).setUp()
        self.global_env = self.useFixture(common.GlobalRequirements())
        self.pbr = self.useFixture(common.pbr_fixture)

    def test_project(self):
        update.main(['--source', self.global_env.root, self.pbr.root])
        reqs = common._file_to_list(self.pbr.req_file)
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_test_project(self):
        update.main(['--source', self.global_env.root, self.pbr.root])
        reqs = common._file_to_list(self.pbr.test_req_file)
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        update.main(['--source', self.global_env.root, self.pbr.root])
        setup_contents = common._file_to_list(self.pbr.setup_file)
        self.assertNotIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS "
                         "REPO - DO NOT EDIT", setup_contents)
