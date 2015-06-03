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


def _file_to_list(fname):
    with open(fname) as f:
        content = list(map(lambda x: x.rstrip(), f.readlines()))
        print(content)
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
    "tests/files/project.txt",
    "tests/files/setup.py", "tests/files/setup.cfg",
    "tests/files/test-project.txt")
bad_project_fixture = Project(
    "tests/files/project-with-bad-requirement.txt", "tests/files/setup.py",
    "tests/files/setup.cfg")
oslo_fixture = Project(
    "tests/files/project-with-oslo-tar.txt", "tests/files/old-setup.py",
    "tests/files/setup.cfg")
pbr_fixture = Project(
    "tests/files/project.txt", "tests/files/setup.py",
    "tests/files/pbr_setup.cfg", "tests/files/test-project.txt")


class GlobalRequirements(fixtures.Fixture):

    def setUp(self):
        super(GlobalRequirements, self).setUp()
        self.root = self.useFixture(fixtures.TempDir()).path
        self.req_file = os.path.join(self.root, "global-requirements.txt")
        shutil.copy("tests/files/gr-base.txt", self.req_file)
