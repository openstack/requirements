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

from openstack_requirements.cmds import build_lower_constraints
from openstack_requirements import requirement


class BuildLowerConstraintsTest(testtools.TestCase):

    def test_one_input_file(self):
        inputs = [
            requirement.parse('package==1.2.3'),
        ]
        expected = [
            'package==1.2.3\n',
        ]
        self.assertEqual(
            expected,
            list(build_lower_constraints.merge_constraints_sets(inputs))
        )

    def test_two_input_file_same(self):
        inputs = [
            requirement.parse('package==1.2.3'),
            requirement.parse('package==1.2.3'),
        ]
        expected = [
            'package==1.2.3\n',
        ]
        self.assertEqual(
            expected,
            list(build_lower_constraints.merge_constraints_sets(inputs))
        )

    def test_two_input_file_differ(self):
        inputs = [
            requirement.parse('package==1.2.3'),
            requirement.parse('package==4.5.6'),
        ]
        expected = [
            'package==4.5.6\n',
        ]
        self.assertEqual(
            expected,
            list(build_lower_constraints.merge_constraints_sets(inputs))
        )

    def test_one_input_file_with_comments(self):
        inputs = [
            requirement.parse('package==1.2.3\n # package2==0.9.8'),
        ]
        expected = [
            'package==1.2.3\n',
        ]
        self.assertEqual(
            expected,
            list(build_lower_constraints.merge_constraints_sets(inputs))
        )
