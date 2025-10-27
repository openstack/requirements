# Copyright 2012 OpenStack Foundation
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
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

"""The project abstraction."""

import configparser
import errno
import io
import os


def extras(project):
    """Return a dict of extra-name:content for the extras in setup.cfg."""
    if 'setup.cfg' not in project:
        return {}
    c = configparser.ConfigParser()
    c.read_file(io.StringIO(project['setup.cfg']))
    if not c.has_section('extras'):
        return {}
    return dict(c.items('extras'))


# IO from here to the end of the file.


def _safe_read(project, filename, output=None):
    if output is None:
        output = project
    try:
        path = os.path.join(project['root'], filename)
        with open(path, encoding="utf-8") as f:
            output[filename] = f.read()
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def read(root):
    """Read into memory the packaging data for the project at root.

    :param root: A directory path.
    :return: A dict representing the project with the following keys:
        - root: The root dir.
        - setup.py: Contents of setup.py.
        - setup.cfg: Contents of setup.cfg.
        - requirements: Dict of requirement file name: contents.
    """
    result = {'root': root}
    _safe_read(result, 'setup.py')
    _safe_read(result, 'setup.cfg')

    requirements = {}
    result['requirements'] = requirements
    for target_file in [
        'requirements.txt',
        'test-requirements.txt',
        'doc/requirements.txt',
        # deprecated aliases (warnings are handled elsewhere)
        'tools/pip-requires',
        'tools/test-requires',
        'requirements-py2.txt',
        'requirements-py3.txt',
        'test-requirements-py2.txt',
        'test-requirements-py3.txt',
    ]:
        _safe_read(result, target_file, output=requirements)
    return result
