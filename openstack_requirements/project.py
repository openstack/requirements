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


def _read_setup_cfg_extras(root):
    data = _read_raw(root, 'setup.cfg')
    if data is None:
        return None

    c = configparser.ConfigParser()
    c.read_file(io.StringIO(data))
    if c.has_section('extras'):
        return dict(c.items('extras'))

    return None


def _read_raw(root, filename):
    try:
        path = os.path.join(root, filename)
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def read(root):
    """Read into memory the packaging data for the project at root.

    :param root: A directory path.
    :return: A dict representing the project with the following keys:
        - root: The root dir.
        - requirements: Dict of requirement file name
        - extras: Dict of extras file name to a dict of extra names and
          requirements
    """
    # Store root directory and installer-related files for later processing
    result = {'root': root}

    # Store requirements
    result['requirements'] = {}

    for filename in [
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
        if (data := _read_raw(root, filename)) is not None:
            result['requirements'][filename] = data

    # Store extras
    result['extras'] = {}
    if (data := _read_setup_cfg_extras(root)) is not None:
        result['extras']['setup.cfg'] = data

    return result
