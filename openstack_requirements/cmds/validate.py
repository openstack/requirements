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

"""Apply validation rules to the various requirements lists."""

import argparse
import os

from openstack_requirements import constraints
from openstack_requirements import requirement
from openstack_requirements.utils import read_requirements_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'global_requirements',
        default='global-requirements.txt',
        help='path to the global-requirements.txt file',
    )
    parser.add_argument(
        'upper_constraints',
        default='upper-constraints.txt',
        help='path to the upper-constraints.txt file',
    )
    parser.add_argument(
        'denylist',
        default='denylist.txt',
        help='path to the denylist.txt file',
    )
    args = parser.parse_args()

    error_count = 0

    # Check the format of the constraints file.
    print(f'\nChecking {args.upper_constraints}')
    constraints_txt = read_requirements_file(args.upper_constraints)
    for msg in constraints.check_format(constraints_txt):
        print(msg)
        error_count += 1

    # Check that the constraints and requirements are compatible.
    print(f'\nChecking {args.global_requirements}')
    global_reqs = read_requirements_file(args.global_requirements)
    for msg in constraints.check_compatible(global_reqs, constraints_txt):
        print(msg)
        error_count += 1

    # Check requirements to satisfy policy.
    print(f'\nChecking requirements on {args.global_requirements}')
    for msg in requirement.check_reqs_bounds_policy(global_reqs):
        print(msg)
        error_count += 1

    # Check that global requirements are uniformly formatted
    print(f'\nValidating uniform formatting on {args.global_requirements}')
    with open(args.global_requirements) as f:
        for line in f:
            if line == '\n':
                continue
            req = requirement.parse_line(line)
            normed_req = req.to_line(comment_prefix='  ', sort_specifiers=True)
            if line.rstrip() != normed_req.rstrip():
                print(f"-{line.rstrip()}\n+{normed_req.rstrip()}")
                error_count += 1

    # Check that all of the items in the global-requirements list
    # appear in exactly one of the constraints file or the denylist.
    print(f'\nChecking {args.denylist}')
    denylist = read_requirements_file(args.denylist)
    for msg in constraints.check_denylist_coverage(
        global_reqs,
        constraints_txt,
        denylist,
        os.path.basename(args.upper_constraints),
    ):
        print(msg)
        error_count += 1

    return 1 if error_count else 0
