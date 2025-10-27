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

from openstack_requirements import project
from openstack_requirements import requirement


def _file_to_list(fname):
    with open(fname) as f:
        content = list(map(lambda x: x.rstrip(), f.readlines()))
        return content


class Project(fixtures.Fixture):
    """A single project we can update."""

    def __init__(
        self,
        req_path=None,
        setup_path=None,
        setup_cfg_path=None,
        test_req_path=None,
        pyproject_toml_path=None,
    ):
        super().__init__()
        self._req_path = req_path
        self._setup_path = setup_path
        self._setup_cfg_path = setup_cfg_path
        self._test_req_path = test_req_path
        self._pyproject_toml_path = pyproject_toml_path

    def setUp(self):
        super().setUp()
        self.root = self.useFixture(fixtures.TempDir()).path

        self.req_file = os.path.join(self.root, 'requirements.txt')
        if self._req_path:
            shutil.copy(self._req_path, self.req_file)

        self.setup_file = os.path.join(self.root, 'setup.py')
        if self._setup_path:
            shutil.copy(self._setup_path, self.setup_file)

        self.setup_cfg_file = os.path.join(self.root, 'setup.cfg')
        if self._setup_cfg_path:
            shutil.copy(self._setup_cfg_path, self.setup_cfg_file)

        self.test_req_file = os.path.join(self.root, 'test-requirements.txt')
        if self._test_req_path:
            shutil.copy(self._test_req_path, self.test_req_file)

        self.pyproject_toml_file = os.path.join(self.root, 'pyproject.toml')
        if self._pyproject_toml_path:
            shutil.copy(self._pyproject_toml_path, self.pyproject_toml_file)


project_fixture = Project(
    "openstack_requirements/tests/files/project.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/setup.cfg",
    "openstack_requirements/tests/files/test-project.txt",
)
bad_project_fixture = Project(
    "openstack_requirements/tests/files/project-with-bad-requirement.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/setup.cfg",
)
oslo_fixture = Project(
    "openstack_requirements/tests/files/project-with-oslo-tar.txt",
    "openstack_requirements/tests/files/old-setup.py",
    "openstack_requirements/tests/files/setup.cfg",
)
pbr_fixture = Project(
    "openstack_requirements/tests/files/project.txt",
    "openstack_requirements/tests/files/setup.py",
    "openstack_requirements/tests/files/pbr_setup.cfg",
    "openstack_requirements/tests/files/test-project.txt",
)
pep_518_fixture = Project(
    pyproject_toml_path="openstack_requirements/tests/files/pyproject.toml",
)


class GlobalRequirements(fixtures.Fixture):
    def setUp(self):
        super().setUp()
        self.root = self.useFixture(fixtures.TempDir()).path
        self.req_file = os.path.join(self.root, "global-requirements.txt")
        shutil.copy(
            "openstack_requirements/tests/files/gr-base.txt", self.req_file
        )
        self.denylist_file = os.path.join(self.root, "denylist.txt")
        shutil.copy(
            "openstack_requirements/tests/files/denylist.txt",
            self.denylist_file,
        )


# Static data for unit testing.
def make_project(fixture):
    with fixture:
        return project.read(fixture.root)


global_reqs = requirement.parse(
    open("openstack_requirements/tests/files/gr-base.txt").read()
)
upper_constraints = requirement.parse(
    open("openstack_requirements/tests/files/upper-constraints.txt").read()
)
denylist = requirement.parse(
    open("openstack_requirements/tests/files/denylist.txt").read()
)
project_project = make_project(project_fixture)
