# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack, LLC
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

r"""
A simple script to update the requirements files from a global set of
allowable requirements.

The script can be called like this:

  $> python update.py ../myproj

Any requirements listed in the target files will have their versions
updated to match the global requirements. Requirements not in the global
files will be dropped.
"""

import os
import os.path
import sys

from pip import req


_setup_py_text = """#!/usr/bin/env python
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
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

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
import setuptools

setuptools.setup(
    setup_requires=['pbr>=0.5.20'],
    pbr=True)
"""


def _parse_pip(pip):

    install_require = req.InstallRequirement.from_line(pip)
    if install_require.editable:
        return pip
    elif install_require.url:
        return pip
    else:
        return install_require.req.key


def _pass_through(pip):
    return (not pip or
            pip.startswith('#') or
            pip.startswith('http://tarballs.openstack.org/') or
            pip.startswith('-e') or
            pip.startswith('-f'))


def _parse_reqs(filename):

    reqs = dict()

    pip_requires = open(filename, "r").readlines()
    for pip in pip_requires:
        pip = pip.strip()
        if _pass_through(pip):
            continue
        reqs[_parse_pip(pip)] = pip
    return reqs


def _sync_requirements_file(source_reqs, dest_path):
    dest_reqs = []
    with open(dest_path, 'r') as dest_reqs_file:
        dest_reqs = dest_reqs_file.readlines()

    print("Syncing %s" % dest_path)

    with open(dest_path, 'w') as new_reqs:
        for old_line in dest_reqs:
            old_require = old_line.strip()

            if _pass_through(old_require):
                new_reqs.write(old_line)
                continue

            old_pip = _parse_pip(old_require.lower())

            # Special cases:
            # projects need to align pep8 version on their own time
            if "pep8" in old_pip:
                new_reqs.write(old_line)
                continue

            if old_pip in source_reqs:
                new_reqs.write("%s\n" % source_reqs[old_pip])


def _copy_requires(source_path, dest_dir):
    """Copy requirements files."""

    source_reqs = _parse_reqs(source_path)

    target_files = (
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires')

    for dest in target_files:
        dest_path = os.path.join(dest_dir, dest)
        if os.path.exists(dest_path):
            print("_sync_requirements_file(%s, %s)" % (source_reqs, dest_path))
            _sync_requirements_file(source_reqs, dest_path)


def _write_setup_py(dest_path):
    print("Syncing setup.py")
    target_setup_py = os.path.join(dest_path, 'setup.py')
    has_pbr = 'pbr' in open(target_setup_py, 'r').read()
    if has_pbr:
        # We only want to sync things that are up to date with pbr mechanics
        with open(target_setup_py, 'w') as setup_file:
            setup_file.write(_setup_py_text)


def main(argv):
    _copy_requires('global-requirements.txt', argv[0])
    _write_setup_py(argv[0])


if __name__ == "__main__":
    main(sys.argv[1:])
