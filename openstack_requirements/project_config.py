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

"""Work with the project-config repository.
"""

import requests
import yaml


ZUUL_PROJECTS_URL = 'https://git.openstack.org/cgit/openstack-infra/project-config/plain/zuul.d/projects.yaml'  # noqa
ZUUL_PROJECTS_FILENAME = 'openstack-infra/project-config/zuul.d/projects.yaml'


def get_zuul_projects_data(url=ZUUL_PROJECTS_URL):
    """Return the parsed data structure for the zuul.d/projects.yaml file.

    :param url: Optional URL to the location of the file. Defaults to
      the most current version in the public git repository.

    """
    r = requests.get(url)
    raw = yaml.safe_load(r.text)
    # Add a mapping from repo name to repo settings, since that is how
    # we access this most often.
    projects = {
        p['project']['name']: p['project']
        for p in raw
    }
    return projects


def require_check_requirements_for_repo(zuul_projects, repo):
    """Check the repository for the jobs related to requirements.

    Returns a list of error messages.

    """
    errors = []

    if repo not in zuul_projects:
        errors.append(
            ('did not find %s in %s' % (repo, ZUUL_PROJECTS_FILENAME),
             True)
        )
    else:
        p = zuul_projects[repo]
        templates = p.get('templates', [])
        # NOTE(dhellmann): We don't mess around looking for individual
        # jobs, because we want projects to use the templates.
        if 'check-requirements' not in templates:
            errors.append(
                '%s no check-requirements job specified for %s'
                % (ZUUL_PROJECTS_FILENAME, repo)
            )
    return errors
