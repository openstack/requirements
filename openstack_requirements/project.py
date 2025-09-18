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
        with io.open(path, 'rt', encoding="utf-8") as f:
            output[filename] = f.read()
    except IOError as e:
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
    target_files = [
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
        'doc/requirements.txt',
    ]
    for py_version in (2, 3):
        target_files.append('requirements-py%s.txt' % py_version)
        target_files.append('test-requirements-py%s.txt' % py_version)
    for target_file in target_files:
        _safe_read(result, target_file, output=requirements)
    # Read lower-constraints.txt and ensure the key is always present
    # in case the file is missing.
    result['lower-constraints.txt'] = None
    _safe_read(result, 'lower-constraints.txt')
    return result
