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

"""Check to see if a package from a project's requrements file exist in g-r or
u-c.

"""

import argparse

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from openstack_requirements import project
from openstack_requirements import requirement
from openstack_requirements.utils import read_requirements_file


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'project', default='', help='path to the project source root folder.'
    )
    parser.add_argument(
        '-u',
        '--upper-constraints',
        default='upper-constraints.txt',
        help='path to the upper-constraints.txt file',
    )
    parser.add_argument(
        '-g',
        '--global-requirements',
        default='global-requirements.txt',
        help='Path to the global-requirements.txt file',
    )
    parser.add_argument(
        '-b',
        '-d',
        '--denylist',
        default='denylist.txt',
        help='Path to the denylist.txt file',
    )
    parser.add_argument(
        '-G',
        '--gr-check',
        action='store_true',
        help='Do a specifier check of global-requirements',
    )
    args = parser.parse_args(args)

    upper_constraints = read_requirements_file(args.upper_constraints)
    global_requirements = read_requirements_file(args.global_requirements)
    denylist = read_requirements_file(args.denylist)
    project_data = project.read(args.project)
    error_count = 0

    for require_file, data in project_data.get('requirements', {}).items():
        print(
            f'\nComparing {require_file} with global-requirements and upper-constraints'
        )
        requirements = requirement.parse(data)
        for name, spec_list in requirements.items():
            if not name or name in denylist:
                continue
            if name not in global_requirements:
                print(
                    f'{name} from {require_file} not found in global-requirements'
                )
                error_count += 1
                continue
            if name not in upper_constraints:
                print(
                    f'{name} from {require_file} not found in upper-constraints'
                )
                error_count += 1
                continue
            elif spec_list:
                uc = upper_constraints[name][0][0]
                gr = global_requirements[name][0][0]
                spec_gr = SpecifierSet(gr.specifiers)
                for req, _ in spec_list:
                    specs = SpecifierSet(req.specifiers)
                    # This assumes uc will only have == specifiers
                    for uc_spec in SpecifierSet(uc.specifiers):
                        # if the uc version isn't in the lower specifier
                        # then something is wrong.
                        if Version(uc_spec.version) not in specs:
                            print(
                                f'{name} must be <= {uc_spec.version} from upper-constraints and '
                                'include the upper-constraints version'
                            )
                            error_count += 1
                            continue
                    if args.gr_check:
                        for spec in specs:
                            # g-r will mostly define blocked versions. And a
                            # local project may define there own, so there is
                            # no point checking a != specifier
                            if spec.operator == '!=':
                                continue
                            if spec.version not in spec_gr:
                                print(
                                    f'Specifier {spec.version} from {name} is failing check '
                                    f'from global-requirements specifiers {str(spec_gr)}'
                                )
                                error_count += 1
                                continue

    return 1 if error_count else 0
