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

import fixtures
from packaging import specifiers
import testtools

from openstack_requirements import requirement


def check_compatible(global_reqs, constraints):
    """Check compatibility between requirements and constraints.

    A change to global-requirements that wants to make changes
    incompatible with the current frozen constraints needs to also raise
    those constraints.
    Load global-requirements
    Load upper-constraints.txt
    Check that every version within upper-constraints.txt is either
    A) Missing from global-requirements - its a transitive dep or
       a removed dep.
    B) Compatible with any of the versions in global-requirements.
       This is not-quite right, because we should in principle match
       markers, but that requires evaluating the markers which we
       haven't yet implemented. Being compatible with one of the
       requirements is good enough proxy to catch most cases.

    :param global_reqs: A set of global requirements after parsing.
    :param constraints: The same from upper-constraints.txt.
    :return: A list of the parsed package tuples that failed.
    """
    failures = []

    def satisfied(reqs, name, version):
        if name not in reqs:
            return True
        tested = []
        for constraint, _ in reqs[name]:
            spec = specifiers.SpecifierSet(constraint.specifiers)
            if spec.contains(version):
                return True
            tested.append(constraint.specifiers)
        print('Constraint for %s==%s does not match %s' %
              (name, version, tested))
        return False
    for pkg_constraints in constraints.values():
        for constraint, _ in pkg_constraints:
            name = constraint.package
            version = constraint.specifiers[3:]
            if not satisfied(global_reqs, name, version):
                failures.append(constraint)
    return failures


class TestRequirements(testtools.TestCase):

    def setUp(self):
        super(TestRequirements, self).setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

    def test_constraints_format(self):
        errors = 0
        constraints_content = open('upper-constraints.txt', 'rt').read()
        for n, line in enumerate(constraints_content.splitlines(), 1):
            c = requirement.parse_line(line)
            spec = c.specifiers
            if not spec.startswith('==='):
                print(
                    'Invalid constraint line %d %r, does not have 3 "="' %
                    (n, line)
                )
                errors += 1
        if errors:
            self.fail('Encountered errors parsing constraints.txt')

    def test_constraints_compatible(self):
        global_req_content = open('global-requirements.txt', 'rt').read()
        constraints_content = open('upper-constraints.txt', 'rt').read()
        global_reqs = requirement.parse(global_req_content)
        constraints = requirement.parse(constraints_content)
        self.assertEqual([], check_compatible(global_reqs, constraints))


class TestCheckCompatible(testtools.TestCase):

    def setUp(self):
        super(TestCheckCompatible, self).setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

    def test_non_requirement(self):
        global_reqs = {}
        good_constraints = requirement.parse("foo===1.2.5\n")
        self.assertEqual(
            [],
            check_compatible(global_reqs, good_constraints)
        )

    def test_compatible(self):
        global_reqs = requirement.parse("foo>=1.2\nbar>2.0\n")
        good_constraints = requirement.parse("foo===1.2.5\n")
        self.assertEqual(
            [],
            check_compatible(global_reqs, good_constraints)
        )

    def test_constraint_below_range(self):
        global_reqs = requirement.parse("oslo.concurrency>=2.3.0\nbar>1.0\n")
        bad_constraints = requirement.parse("oslo.concurrency===2.2.0\n")
        results = check_compatible(global_reqs, bad_constraints)
        self.assertNotEqual([], results)

    def test_constraint_above_range(self):
        global_reqs = requirement.parse("foo>=1.2,<2.0\nbar>1.0\n")
        bad_constraints = requirement.parse("foo===2.0.1\n")
        results = check_compatible(global_reqs, bad_constraints)
        self.assertNotEqual([], results)
