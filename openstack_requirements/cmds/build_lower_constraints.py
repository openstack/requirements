# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Merge multiple lower-constraints.txt files to find the highest values.

"""

import argparse
import collections

from openstack_requirements import requirement

import packaging.specifiers
import packaging.version


def read_requirements_file(filename):
    with open(filename, 'rt') as f:
        body = f.read()
    return requirement.parse(body)


def get_requirements_version(req):
    """Find the version for a requirement.

    Use the version attached to >=, ==, or ===, depending on the type
    of input requirement.

    """
    for specifier in packaging.specifiers.SpecifierSet(req.specifiers):
        if '>=' in specifier.operator or '==' in specifier.operator:
            return packaging.version.parse(specifier.version)
    raise ValueError('could not find version for {}'.format(req))


def merge_constraints_sets(constraints_sets):
    "Generator of Requirements with the maximum version for each constraint."
    all_constraints = collections.defaultdict(list)
    for constraints_set in constraints_sets:
        for constraint_name, constraint in constraints_set.items():
            if constraint_name:
                all_constraints[constraint_name].extend(constraint)
    for constraint_name, constraints in sorted(all_constraints.items()):
        val = max((c[0] for c in constraints), key=get_requirements_version)
        yield val.to_line()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'lower_constraints',
        nargs='+',
        help='lower-constraints.txt files',
    )
    args = parser.parse_args()

    constraints_sets = [
        read_requirements_file(filename)
        for filename in args.lower_constraints
    ]

    merged = list(merge_constraints_sets(constraints_sets))
    print(''.join(merged))
