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

import testtools

from openstack_requirements.cmds import update
from openstack_requirements import project
from openstack_requirements.tests import common


class UpdateTestWithSuffix(testtools.TestCase):

    def test_project(self):
        reqs = common.project_file(
            self.fail, common.project_project, 'requirements.txt.global',
            suffix='global')
        # ensure various updates take
        self.assertIn("jsonschema!=1.4.0,<2,>=1.0.0", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy<=0.7.99,>=0.7", reqs)

    def test_project_with_oslo(self):
        reqs = common.project_file(
            self.fail, common.oslo_project, 'requirements.txt.global',
            suffix='global')
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)

    def test_test_project(self):
        reqs = common.project_file(
            self.fail, common.project_project, 'test-requirements.txt.global',
            suffix='global')
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
            common.oslo_project, common.global_reqs, 'global', None, None,
            False)
        for action in actions:
            if type(action) is project.File:
                self.assertNotEqual(action.filename, 'setup.py')
