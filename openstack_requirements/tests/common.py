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

import os.path
import shutil

import fixtures

from openstack_requirements.cmds import update
from openstack_requirements import project
from openstack_requirements import requirement


def _file_to_list(fname):
    with open(fname) as f:
        content = list(map(lambda x: x.rstrip(), f.readlines()))
        return content


class Project(fixtures.Fixture):
    """A single project we can update."""

    def __init__(
            self, req_path, setup_path, setup_cfg_path, test_req_path=None):
        super(Project, self).__init__()
        self._req_path = req_path
        self._setup_path = setup_path
        self._setup_cfg_path = setup_cfg_path
        self._test_req_path = test_req_path

    def setUp(self):
        super(Project, self).setUp()
        self.root = self.useFixture(fixtures.TempDir()).path
        self.req_file = os.path.join(self.root, 'requirements.txt')
        self.setup_file = os.path.join(self.root, 'setup.py')
        self.setup_cfg_file = os.path.join(self.root, 'setup.cfg')
        self.test_req_file = os.path.join(self.root, 'test-requirements.txt')
        shutil.copy(self._req_path, self.req_file)
        shutil.copy(self._setup_path, self.setup_file)
        shutil.copy(self._setup_cfg_path, self.setup_cfg_file)
        if self._test_req_path:
            shutil.copy(self._test_req_path, self.test_req_file)


project_fixture = Project(
    "openstack_requirements/tests/files/project.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/setup.cfg",
    "openstack_requirements/tests/files/test-project.txt")
bad_project_fixture = Project(
    "openstack_requirements/tests/files/project-with-bad-requirement.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/setup.cfg")
oslo_fixture = Project(
    "openstack_requirements/tests/files/project-with-oslo-tar.txt",
    "openstack_requirements/tests/files/old-setup.py",
    "openstack_requirements/tests/files/setup.cfg")
pbr_fixture = Project(
    "openstack_requirements/tests/files/project.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/pbr_setup.cfg",
    "openstack_requirements/tests/files/test-project.txt")


class GlobalRequirements(fixtures.Fixture):

    def setUp(self):
        super(GlobalRequirements, self).setUp()
        self.root = self.useFixture(fixtures.TempDir()).path
        self.req_file = os.path.join(self.root, "global-requirements.txt")
        shutil.copy(
            "openstack_requirements/tests/files/gr-base.txt", self.req_file)
        self.blacklist_file = os.path.join(self.root, "blacklist.txt")
        shutil.copy(
            "openstack_requirements/tests/files/blacklist.txt",
            self.blacklist_file)


# Static data for unit testing.
def make_project(fixture):
    with fixture:
        return project.read(fixture.root)


global_reqs = requirement.parse(
    open("openstack_requirements/tests/files/gr-base.txt", "rt").read())
upper_constraints = requirement.parse(
    open("openstack_requirements/tests/files/upper-constraints.txt",
         "rt").read())
blacklist = requirement.parse(
    open("openstack_requirements/tests/files/blacklist.txt", "rt").read())
pbr_project = make_project(pbr_fixture)
project_project = make_project(project_fixture)
bad_project = make_project(bad_project_fixture)
oslo_project = make_project(oslo_fixture)


def project_file(
        fail, proj, action_filename, suffix=None, softupdate=None,
        non_std_reqs=False, blacklist={}):
    actions = update._process_project(
        proj, global_reqs, suffix, softupdate, None,
        non_std_reqs, blacklist)
    for action in actions:
        if type(action) is project.File:
            if action.filename == action_filename:
                return action.content.splitlines()
    fail('File %r not found in %r' % (action_filename, actions))
