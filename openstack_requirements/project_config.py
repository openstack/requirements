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


ZUUL_LAYOUT_URL = 'http://git.openstack.org/cgit/openstack-infra/project-config/plain/zuul/layout.yaml'  # noqa
ZUUL_LAYOUT_FILENAME = 'openstack-infra/project-config/zuul/layout.yaml'

# We use this key to modify the data structure read from the zuul
# layout file. We don't control what are valid keys there, so make it
# easy to change the key we use, just in case.
_VALIDATE_KEY = 'validate-projects-by-name'


def get_zuul_layout_data(url=ZUUL_LAYOUT_URL):
    """Return the parsed data structure for the zuul/layout.yaml file.

    :param url: Optional URL to the location of the file. Defaults to
      the most current version in the public git repository.

    """
    r = requests.get(url)
    raw = yaml.safe_load(r.text)
    # Add a mapping from repo name to repo settings, since that is how
    # we access this most often.
    raw[_VALIDATE_KEY] = {
        p['name']: p
        for p in raw['projects']
    }
    return raw


def require_check_requirements_for_repo(zuul_layout, repo):
    """Check the repository for the jobs related to requirements.

    Returns a list of error messages.

    """
    errors = []

    if repo not in zuul_layout[_VALIDATE_KEY]:
        errors.append(
            ('did not find %s in %s' % (repo, ZUUL_LAYOUT_FILENAME),
             True)
        )
    else:
        p = zuul_layout[_VALIDATE_KEY][repo]
        templates = [
            t['name']
            for t in p.get('template', [])
        ]
        # NOTE(dhellmann): We don't mess around looking for individual
        # jobs, because we want projects to use the templates.
        if 'check-requirements' not in templates:
            errors.append(
                '%s no check-requirements job specified for %s'
                % (ZUUL_LAYOUT_FILENAME, repo)
            )
    return errors
