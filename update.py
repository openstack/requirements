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

VERBOSE = None

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

# In python < 2.7.4, a lazy loading of package `pbr` will break
# setuptools if some other modules registered functions in `atexit`.
# solution from: http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing  # noqa
except ImportError:
    pass

setuptools.setup(
    setup_requires=['pbr'],
    pbr=True)
"""


# A header for the requirements file(s).
_REQS_HEADER = [
    '# The order of packages is significant, because pip processes '
    'them in the order\n',
    '# of appearance. Changing the order has an impact on the overall '
    'integration\n',
    '# process, which may cause wedges in the gate later.\n',
]


def verbose(msg):
    if VERBOSE:
        print(msg)


class Change(object):
    def __init__(self, name, old, new):
        self.name = name
        self.old = old
        self.new = new

    def __repr__(self):
        return "%-30.30s ->   %s" % (self.old, self.new)


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


def _functionally_equal(old_requirement, new_requirement):
    old_require = req.InstallRequirement.from_line(old_requirement)
    new_require = req.InstallRequirement.from_line(new_requirement)
    return old_require.req == new_require.req


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


def _sync_requirements_file(source_reqs, dev_reqs, dest_path,
                            suffix, softupdate):
    dest_reqs = _readlines(dest_path)
    changes = []
    # this is specifically for global-requirements gate jobs so we don't
    # modify the git tree
    if suffix:
        dest_path = "%s.%s" % (dest_path, suffix)

    verbose("Syncing %s" % dest_path)

    with open(dest_path, 'w') as new_reqs:

        # Check the instructions header
        if dest_reqs[:len(_REQS_HEADER)] != _REQS_HEADER:
            new_reqs.writelines(_REQS_HEADER)

        for old_line in dest_reqs:
            old_require = old_line.strip()

            if _pass_through(old_require):
                new_reqs.write(old_line)
                continue

            old_pip = _parse_pip(old_require.lower())

            # Special cases:
            # projects need to align hacking version on their own time
            if "hacking" in old_pip:
                new_reqs.write(old_line)
                continue

            if old_pip in source_reqs:
                # allow it to be in dev-requirements
                if ((old_pip in dev_reqs) and (old_require.lower() ==
                                               dev_reqs[old_pip])):
                    new_reqs.write("%s\n" % dev_reqs[old_pip])
                elif _functionally_equal(old_require, source_reqs[old_pip]):
                    new_reqs.write(old_line)
                else:
                    changes.append(
                        Change(old_pip, old_require, source_reqs[old_pip]))
                    new_reqs.write("%s\n" % source_reqs[old_pip])
            elif softupdate:
                # under softupdate we pass through anything we don't
                # understand, this is intended for ecosystem projects
                # that want to stay in sync with existing
                # requirements, but also add their own above and
                # beyond
                new_reqs.write(old_line)
            else:
                # What do we do if we find something unexpected?
                #
                # In the default cause we should die horribly, because
                # the point of global requirements was a single lever
                # to control all the pip installs in the gate.
                #
                # However, we do have other projects using
                # devstack jobs that might have legitimate reasons to
                # override. For those we support NON_STANDARD_REQS=1
                # environment variable to turn this into a warning only.
                print("'%s' is not in global-requirements.txt" % old_pip)
                if os.getenv('NON_STANDARD_REQS', '0') != '1':
                    sys.exit(1)
    # always print out what we did if we did a thing
    if changes:
        print("Version change for: %s" % ", ".join([x.name for x in changes]))
        print("Updated %s:" % dest_path)
        for change in changes:
            print("    %s" % change)


def _copy_requires(suffix, softupdate, dest_dir):
    """Copy requirements files."""

    source_reqs = _parse_reqs('global-requirements.txt')
    dev_reqs = _parse_reqs('dev-requirements.txt')

    target_files = [
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
    ]
    for py_version in (2, 3):
        target_files.append('requirements-py%s.txt' % py_version)
        target_files.append('test-requirements-py%s.txt' % py_version)

    for dest in target_files:
        dest_path = os.path.join(dest_dir, dest)
        if os.path.exists(dest_path):
            _sync_requirements_file(source_reqs, dev_reqs, dest_path,
                                    suffix, softupdate)


def _write_setup_py(dest_path):
    target_setup_py = os.path.join(dest_path, 'setup.py')
    setup_cfg = os.path.join(dest_path, 'setup.cfg')
    # If it doesn't have a setup.py, then we don't want to update it
    if not os.path.exists(target_setup_py):
        return
    has_pbr = 'pbr' in _read(target_setup_py)
    if has_pbr:
        if 'name = pbr' not in _read(setup_cfg):
            verbose("Syncing setup.py")
            # We only want to sync things that are up to date
            # with pbr mechanics
            with open(target_setup_py, 'w') as setup_file:
                setup_file.write(_setup_py_text)


def main(options, args):
    if len(args) != 1:
        print("Must specify directory to update")
        sys.exit(1)
    global VERBOSE
    VERBOSE = options.verbose
    _copy_requires(options.suffix, options.softupdate, args[0])
    _write_setup_py(args[0])


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output-suffix", dest="suffix", default="",
                      help="output suffix for updated files (i.e. .global)")
    parser.add_option("-s", "--soft-update", dest="softupdate",
                      action="store_true",
                      help="Pass through extra requirements without warning.")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true",
                      help="Add further verbosity to output")
    (options, args) = parser.parse_args()
    main(options, args)
