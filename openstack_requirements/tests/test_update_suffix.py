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

import testtools

from openstack_requirements.tests import common
from openstack_requirements import update


class UpdateTestWithSuffix(testtools.TestCase):

    def setUp(self):
        super(UpdateTestWithSuffix, self).setUp()
        self.global_env = self.useFixture(common.GlobalRequirements())

    def test_project(self):
        project = self.useFixture(common.project_fixture)
        update.main(
            ['--source', self.global_env.root, '-o', 'global',
             project.root])
        reqs = common._file_to_list("%s.%s" % (project.req_file, 'global'))
        # ensure various updates take
        self.assertIn("jsonschema>=1.0.0,!=1.4.0,<2", reqs)
        self.assertIn("python-keystoneclient>=0.4.1", reqs)
        self.assertIn("SQLAlchemy>=0.7,<=0.7.99", reqs)

    def test_project_with_oslo(self):
        project = self.useFixture(common.oslo_fixture)
        update.main(
            ['--source', self.global_env.root, '-o', 'global',
             project.root])
        reqs = common._file_to_list("%s.%s" % (project.req_file, 'global'))
        oslo_tar = ("-f http://tarballs.openstack.org/oslo.config/"
                    "oslo.config-1.2.0a3.tar.gz#egg=oslo.config-1.2.0a3")
        self.assertIn(oslo_tar, reqs)

    def test_test_project(self):
        project = self.useFixture(common.project_fixture)
        update.main(
            ['--source', self.global_env.root, '-o', 'global',
             project.root])
        reqs = common._file_to_list(
            "%s.%s" % (project.test_req_file, 'global'))
        self.assertIn("testtools>=0.9.32", reqs)
        self.assertIn("testrepository>=0.0.17", reqs)
        # make sure we didn't add something we shouldn't
        self.assertNotIn("sphinxcontrib-pecanwsme>=0.2", reqs)

    def test_install_setup(self):
        project = self.useFixture(common.project_fixture)
        update.main(
            ['--source', self.global_env.root, '-o', 'global',
             project.root])
        setup_contents = common._file_to_list(project.setup_file)
        self.assertIn("# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
                      " - DO NOT EDIT", setup_contents)

    def test_no_install_setup(self):
        project = self.useFixture(common.oslo_fixture)
        update.main(
            ['--source', self.global_env.root, '-o', 'global',
             project.root])
        setup_contents = common._file_to_list(project.setup_file)
        self.assertNotIn(
            "# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO"
            " - DO NOT EDIT", setup_contents)
