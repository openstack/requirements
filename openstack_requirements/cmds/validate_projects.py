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

"""Apply validation rules to the projects.txt file

"""

import argparse

from openstack_requirements import project_config


_BLACKLIST = set([
    # NOTE(dhellmann): It's not clear why these don't get updates,
    # except that trying to do so may break the test jobs using them
    # because of the nature of the projects.
    'openstack/hacking',
    'openstack/pbr',
    # We can't enforce the check rules against this repo.
    'openstack/requirements',
])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'projects_list',
        default='projects.txt',
        help='path to the projects.txt file',
    )
    args = parser.parse_args()

    zuul_projects = project_config.get_zuul_projects_data()

    error_count = 0

    print('\nChecking %s' % args.projects_list)
    with open(args.projects_list, 'r') as f:
        for repo in f:
            repo = repo.strip()
            if repo.startswith('#'):
                continue
            if repo in _BLACKLIST:
                continue
            pe = project_config.require_check_requirements_for_repo(
                zuul_projects, repo)
            for e in pe:
                print(e)
                error_count += 1

    return 1 if error_count else 0
