# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from openstack_requirements import check
from openstack_requirements import requirement

import fixtures
import testtools


class TestIsReqInGlobalReqs(testtools.TestCase):

    def setUp(self):
        super(TestIsReqInGlobalReqs, self).setUp()

        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

        self.global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        print('global_reqs', self.global_reqs)

    def test_match(self):
        req = requirement.parse('name>=1.2,!=1.4')['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_name_mismatch(self):
        req = requirement.parse('wrongname>=1.2,!=1.4')['wrongname'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_min_mismatch(self):
        req = requirement.parse('name>=1.3,!=1.4')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_extra_exclusion(self):
        req = requirement.parse('name>=1.2,!=1.4,!=1.5')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_missing_exclusion(self):
        req = requirement.parse('name>=1.2')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )
