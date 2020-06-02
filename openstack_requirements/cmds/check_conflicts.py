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

"""Apply validation rules to the various requirements lists.

"""

import argparse
import sys
import traceback

import pkg_resources

from openstack_requirements import requirement


def read_requirements_file(filename):
    with open(filename, 'rt') as f:
        body = f.read()
    return requirement.parse(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'upper_constraints',
        default='upper-constraints.txt',
        help='path to the upper-constraints.txt file')
    parser.add_argument(
        'uc_xfails',
        default='upper-constraints-xfails.txt',
        help='Path to the upper-constraints-xfails.txt file',
    )
    args = parser.parse_args()

    error_count = 0

    print('\nChecking %s' % args.upper_constraints)
    upper_constraints = read_requirements_file(args.upper_constraints)
    xfails = read_requirements_file(args.uc_xfails)
    for name, spec_list in upper_constraints.items():
        try:
            if name:
                pyver = "python_version=='%s.%s'" % (sys.version_info[0],
                                                     sys.version_info[1])
                for req, original_line in spec_list:
                    if req.markers in ["", pyver]:
                        pkg_resources.require(name)
        except pkg_resources.ContextualVersionConflict as e:
            if e.dist.key in xfails:
                xfail_requirement = xfails[e.dist.key][0][0]
                xfail_blacklists = set(xfail_requirement.markers.split(','))
                conflict = e.dist.as_requirement()
                conflict_specifiers = ''.join(conflict.specs[0])
                conflict_name = conflict.name.lower()

                if (e.required_by.issubset(xfail_blacklists) and
                        xfail_requirement.package == conflict_name and
                        conflict_specifiers == xfail_requirement.specifiers):

                    print('XFAIL while checking conflicts '
                          'for %s: %s conflicts with %s' %
                          (name, e.dist, str(e.req)))
                    continue

            print('Checking conflicts for %s:\n'
                  'ContextualVersionConflict: %s' % (name, str(e)))

            traceback.print_exc(file=sys.stdout)
            error_count += 1

    return 1 if error_count else 0
