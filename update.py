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

r"""
A simple script to update the requirements files from a global set of
allowable requirements.

The script can be called like this:

  $> python update.py ../myproj

Any requirements listed in the target files will have their versions
updated to match the global requirements. Requirements not in the global
files will be dropped.
"""

import optparse
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
    setup_requires=['pbr'],
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


def _read(filename):
    with open(filename, 'r') as f:
        return f.read()


def _readlines(filename):
    with open(filename, 'r') as f:
        return f.readlines()


def _parse_reqs(filename):

    reqs = dict()

    pip_requires = _readlines(filename)
    for pip in pip_requires:
        pip = pip.strip()
        if _pass_through(pip):
            continue
        reqs[_parse_pip(pip)] = pip
    return reqs


def _sync_requirements_file(source_reqs, dev_reqs, dest_path, suffix):
    dest_reqs = _readlines(dest_path)

    # this is specifically for global-requirements gate jobs so we don't
    # modify the git tree
    if suffix:
        dest_path = "%s.%s" % (dest_path, suffix)

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
                # allow it to be in dev-requirements
                if ((old_pip in dev_reqs) and (old_require.lower() ==
                                               dev_reqs[old_pip])):
                    new_reqs.write("%s\n" % dev_reqs[old_pip])
                else:
                    new_reqs.write("%s\n" % source_reqs[old_pip])
            else:
                # Found a requirement that isn't in the global requirement file
                # This is not supposed to happen, so exit with a failure.
                print("'%s' is not a global requirement but it should be,"
                      "something went wrong" %
                      old_pip)
                sys.exit(1)


def _copy_requires(suffix, dest_dir):
    """Copy requirements files."""

    source_reqs = _parse_reqs('global-requirements.txt')
    dev_reqs = _parse_reqs('dev-requirements.txt')

    target_files = (
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
        'requirements-py3.txt', 'test-requirements-py3.txt')

    for dest in target_files:
        dest_path = os.path.join(dest_dir, dest)
        if os.path.exists(dest_path):
            print("_sync_requirements_file(%s, %s, %s)" %
                  (source_reqs, dev_reqs, dest_path))
            _sync_requirements_file(source_reqs, dev_reqs, dest_path, suffix)


def _write_setup_py(dest_path):
    target_setup_py = os.path.join(dest_path, 'setup.py')
    setup_cfg = os.path.join(dest_path, 'setup.cfg')
    # If it doesn't have a setup.py, then we don't want to update it
    if not os.path.exists(target_setup_py):
        return
    has_pbr = 'pbr' in _read(target_setup_py)
    is_pbr = 'name = pbr' in _read(setup_cfg)
    if has_pbr and not is_pbr:
        print("Syncing setup.py")
        # We only want to sync things that are up to date with pbr mechanics
        with open(target_setup_py, 'w') as setup_file:
            setup_file.write(_setup_py_text)


def main(options, args):
    if len(args) != 1:
        print("Must specify directory to update")
        sys.exit(1)
    _copy_requires(options.suffix, args[0])
    _write_setup_py(args[0])


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output-suffix", dest="suffix", default="",
                      help="output suffix for updated files (i.e. .global)")
    (options, args) = parser.parse_args()
    main(options, args)
