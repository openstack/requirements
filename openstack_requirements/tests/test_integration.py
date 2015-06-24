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

from packaging import specifiers
import testtools

from openstack_requirements import update


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
        for pkg in global_reqs.values():
            for constraint, _ in pkg:
                spec = specifiers.SpecifierSet(constraint.specifiers)
                if spec.contains(version):
                    return True
        return False
    for pkg_constraints in constraints.values():
        for constraint, _ in pkg_constraints:
            name = constraint.package
            version = constraint.specifiers[3:]
            if not satisfied(global_reqs, name, version):
                failures.append(constraint)
    return failures


class TestRequirements(testtools.TestCase):

    def test_constraints_compatible(self):
        global_req_content = open('global-requirements.txt', 'rt').read()
        constraints_content = open('upper-constraints.txt', 'rt').read()
        global_reqs = update._parse_reqs(global_req_content)
        constraints = update._parse_reqs(constraints_content)
        self.assertEqual([], check_compatible(global_reqs, constraints))

    def test_check_compatible(self):
        global_reqs = update._parse_reqs("foo>=1.2\n")
        good_constraints = update._parse_reqs("foo===1.2.5\n")
        bad_constraints = update._parse_reqs("foo===1.1.2\n")
        self.assertEqual([], check_compatible(global_reqs, good_constraints))
        self.assertNotEqual(
            [], check_compatible(global_reqs, bad_constraints))
