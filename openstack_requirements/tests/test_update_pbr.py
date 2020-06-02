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

import testtools

from openstack_requirements.cmds import update
from openstack_requirements import project
from openstack_requirements.tests import common


class UpdateTestPbr(testtools.TestCase):

    def test_project(self):
        reqs = common.project_file(
            self.fail, common.pbr_project, 'requirements.txt')
        # ensure various updates take
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy<=0.7.99,>=0.7", reqs)

    def test_test_project(self):
        reqs = common.project_file(
            self.fail, common.pbr_project, 'test-requirements.txt')
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_no_install_setup(self):
        actions = update._process_project(
            common.pbr_project, common.global_reqs, None, None, None,
            False)
        for action in actions:
            if type(action) is project.File:
                self.assertNotEqual(action.filename, 'setup.py')
