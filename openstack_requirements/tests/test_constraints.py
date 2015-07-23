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

from openstack_requirements import constraints
from openstack_requirements import requirement


class TestCheckCompatible(testtools.TestCase):

    def test_non_requirement(self):
        global_reqs = {}
        good_constraints = requirement.parse("foo===1.2.5\n")
        self.assertEqual(
            [],
            constraints.check_compatible(global_reqs, good_constraints)
        )

    def test_compatible(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\n")
        self.assertEqual(
            [],
            constraints.check_compatible(global_reqs, good_constraints)
        )

    def test_constraint_below_range(self):
        global_reqs = requirement.parse("oslo.concurrency>=2.3.0\nbar>1.0\n")
        bad_constraints = requirement.parse("oslo.concurrency===2.2.0\n")
        results = constraints.check_compatible(global_reqs, bad_constraints)
        self.assertNotEqual([], results)

    def test_constraint_above_range(self):
        global_reqs = requirement.parse("foo>=1.2,<2.0\nbar>1.0\n")
        bad_constraints = requirement.parse("foo===2.0.1\n")
        results = constraints.check_compatible(global_reqs, bad_constraints)
        self.assertNotEqual([], results)


class TestCheckFormat(testtools.TestCase):

    def test_ok(self):
        good_constraints = requirement.parse("foo===1.2.5\n")
        self.assertEqual(
            [],
            list(constraints.check_format(good_constraints))
        )

    def test_two_equals(self):
        bad_constraints = requirement.parse("foo==1.2.5\n")
        self.assertEqual(
            1,
            len(list(constraints.check_format(bad_constraints)))
        )


class TestBlacklistCoverage(testtools.TestCase):

    def test_constrained(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\nbar==2.1")
        blacklist = requirement.parse('flake8\nhacking')
        self.assertEqual(
            [],
            list(constraints.check_blacklist_coverage(
                global_reqs, good_constraints, blacklist, 'test'))
        )

    def test_blacklisted(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\n")
        blacklist = requirement.parse('flake8\nhacking\nbar')
        self.assertEqual(
            [],
            list(constraints.check_blacklist_coverage(
                global_reqs, good_constraints, blacklist, 'test'))
        )

    def test_both(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\nbar>2.0")
        blacklist = requirement.parse('flake8\nhacking\nbar')
        results = list(constraints.check_blacklist_coverage(
            global_reqs, good_constraints, blacklist, 'test'))
        self.assertEqual(1, len(results))
        self.assertIn("'bar' appears in both", results[0])

    def test_neither(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\n")
        blacklist = requirement.parse('flake8\nhacking')
        results = list(constraints.check_blacklist_coverage(
            global_reqs, good_constraints, blacklist, 'test'))
        self.assertEqual(1, len(results))
        self.assertIn("'bar' appears in global-requirements.txt", results[0])
