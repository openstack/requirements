# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from packaging import specifiers


# FIXME(dhellmann): These items were not in the constraints list but
# should not be blacklisted. We don't know yet what versions they
# should have, so just ignore them for a little while until we have
# time to figure that out.
UNCONSTRAINABLE = set([
    'argparse',
    'pip',
    'setuptools',
    'wmi',
    'pywin32',
    'pymi',
    'wheel',
    '',  # blank lines
])


def check_blacklist_coverage(global_reqs, constraints, blacklist,
                             constraints_list_name):
    """Report any items that are not properly constrained.

    Check that all of the items in the global-requirements list
    appear either in the constraints file or the blacklist.
    """
    to_be_constrained = (
        set(global_reqs.keys()) - set(blacklist.keys())
        - UNCONSTRAINABLE
    )
    constrained = set(constraints.keys()) - set([''])
    unconstrained = to_be_constrained - constrained
    for u in sorted(unconstrained):
        yield ('%r appears in global-requirements.txt '
               'but not %s or blacklist.txt' % (u, constraints_list_name))

    # Verify that the blacklist packages are not also listed in
    # the constraints file.
    dupes = constrained.intersection(set(blacklist.keys()))
    for d in dupes:
        yield ('%r appears in both blacklist.txt and %s'
               % (d, constraints_list_name))


def check_format(parsed_constraints):
    "Apply the formatting rules to the pre-parsed constraints."
    for name, spec_list in parsed_constraints.items():
        for req, original_line in spec_list:
            if not req.specifiers.startswith('==='):
                yield ('Invalid constraint for %s does not have 3 "=": %s' %
                       (name, original_line))


def check_compatible(global_reqs, constraints):
    """Check compatibility between requirements and constraints.

    A change to global-requirements that wants to make changes
    incompatible with the current frozen constraints needs to also raise
    those constraints.

    * Load global-requirements
    * Load given constraints.txt
    * Check that every version within given constraints.txt is either

      A) Missing from global-requirements - its a transitive dep or
         a removed dep.
      B) Compatible with any of the versions in global-requirements.
         This is not-quite right, because we should in principle match
         markers, but that requires evaluating the markers which we
         haven't yet implemented. Being compatible with one of the
         requirements is good enough proxy to catch most cases.

    :param global_reqs: A set of global requirements after parsing.
    :param constraints: The same from given constraints.txt.
    :return: A list of the error messages for constraints that failed.
    """
    def satisfied(reqs, name, version, failures):
        if name not in reqs:
            return True
        tested = []
        for constraint, _ in reqs[name]:
            spec = specifiers.SpecifierSet(constraint.specifiers)
            # pre-releases are allowed by policy but discouraged
            if spec.contains(version, prereleases=True):
                return True
            tested.append(constraint.specifiers)
        failures.append('Constraint %s for %s does not match requirement %s' %
                        (version, name, tested))
        return False
    failures = []
    for pkg_constraints in constraints.values():
        for constraint, _ in pkg_constraints:
            name = constraint.package
            version = constraint.specifiers[3:]
            satisfied(global_reqs, name, version, failures)
    return failures
