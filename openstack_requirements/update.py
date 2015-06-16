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

"""
A simple script to update the requirements files from a global set of
allowable requirements.

The script can be called like this:

  $> python update.py ../myproj

Any requirements listed in the target files will have their versions
updated to match the global requirements. Requirements not in the global
files will be dropped.
"""

import collections
import errno
import optparse
import os
import os.path
import sys

import pkg_resources

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
# TODO(lifeless): Remove this once constraints are in use.
_REQS_HEADER = [
    '# The order of packages is significant, because pip processes '
    'them in the order\n',
    '# of appearance. Changing the order has an impact on the overall '
    'integration\n',
    '# process, which may cause wedges in the gate later.\n',
]


# Pure --
class Change(object):
    def __init__(self, name, old, new):
        self.name = name
        self.old = old
        self.new = new

    def __repr__(self):
        return "%-30.30s ->   %s" % (self.old, self.new)


File = collections.namedtuple('File', ['filename', 'content'])
StdOut = collections.namedtuple('StdOut', ['message'])
Verbose = collections.namedtuple('Verbose', ['message'])


def _package_name(pip_line):
    """Return normalized (lower case) package name.

    This is needed for comparing old and new dictionaries of
    requirements to ensure they match.
    """
    name = pkg_resources.Requirement.parse(pip_line).project_name
    return name.lower()


def _pass_through(pip):
    return (not pip or
            pip.startswith('#') or
            pip.startswith('http://tarballs.openstack.org/') or
            pip.startswith('-e') or
            pip.startswith('-f'))


def _functionally_equal(old_requirement, new_requirement):
    return old_requirement == new_requirement


def _check_setup_py(project):
    actions = []
    # If it doesn't have a setup.py, then we don't want to update it
    if 'setup.py' not in project:
        return actions
    # If it doesn't use pbr, we don't want to update it.
    elif 'pbr' not in project['setup.py']:
        return actions
    # We don't update pbr's setup.py because it can't use itself.
    if 'setup.cfg' in project and 'name = pbr' in project['setup.cfg']:
        return actions
    actions.append(Verbose("Syncing setup.py"))
    actions.append(File('setup.py', _setup_py_text))
    return actions


def _sync_requirements_file(
        source_reqs, content, dest_path, softupdate, hacking, dest_name,
        non_std_reqs):
    actions = []
    dest_reqs = content.splitlines(True)
    changes = []
    # this is specifically for global-requirements gate jobs so we don't
    # modify the git tree

    actions.append(Verbose("Syncing %s" % dest_path))
    content_lines = []

    # Check the instructions header
    if dest_reqs[:len(_REQS_HEADER)] != _REQS_HEADER:
        content_lines.extend(_REQS_HEADER)

    for old_line in dest_reqs:
        old_require = old_line.strip()

        if _pass_through(old_require):
            content_lines.append(old_line)
            continue

        old_pip = _package_name(old_require)

        # Special cases:
        # projects need to align hacking version on their own time
        if "hacking" in old_pip and not hacking:
            content_lines.append(old_line)
            continue

        if old_pip in source_reqs:
            if _functionally_equal(old_require, source_reqs[old_pip]):
                content_lines.append(old_line)
            else:
                changes.append(
                    Change(old_pip, old_require, source_reqs[old_pip]))
                content_lines.append("%s\n" % source_reqs[old_pip])
        elif softupdate:
            # under softupdate we pass through anything we don't
            # understand, this is intended for ecosystem projects
            # that want to stay in sync with existing
            # requirements, but also add their own above and
            # beyond
            content_lines.append(old_line)
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
            actions.append(StdOut(
                "'%s' is not in global-requirements.txt\n" % old_pip))
            if not non_std_reqs:
                raise Exception("nonstandard requirement present.")
    actions.append(File(dest_name, u''.join(content_lines)))
    # always print out what we did if we did a thing
    if changes:
        actions.append(StdOut(
            "Version change for: %s\n"
            % ", ".join([x.name for x in changes])))
        actions.append(StdOut("Updated %s:\n" % dest_path))
        for change in changes:
            actions.append(StdOut("    %s\n" % change))
    return actions


def _copy_requires(
        suffix, softupdate, hacking, project, global_reqs, non_std_reqs):
    """Copy requirements files."""
    actions = []
    for source, content in sorted(project['requirements'].items()):
        dest_path = os.path.join(project['root'], source)
        # this is specifically for global-requirements gate jobs so we don't
        # modify the git tree
        if suffix:
            dest_path = "%s.%s" % (dest_path, suffix)
            dest_name = "%s.%s" % (source, suffix)
        else:
            dest_name = source
        actions.extend(_sync_requirements_file(
            global_reqs, content, dest_path, softupdate, hacking, dest_name,
            non_std_reqs))
    return actions


def _process_project(
        project, global_reqs, suffix, softupdate, hacking, non_std_reqs):
    """Project a project.

    :return: The actions to take as a result.
    """
    actions = _copy_requires(
        suffix, softupdate, hacking, project, global_reqs, non_std_reqs)
    actions.extend(_check_setup_py(project))
    return actions


# IO --
def _safe_read(project, filename, output=None):
    if output is None:
        output = project
    try:
        with open(project['root'] + '/' + filename, 'rt') as f:
            output[filename] = f.read()
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise


def _read_project(root):
    result = {'root': root}
    _safe_read(result, 'setup.py')
    _safe_read(result, 'setup.cfg')
    requirements = {}
    result['requirements'] = requirements
    target_files = [
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
    ]
    for py_version in (2, 3):
        target_files.append('requirements-py%s.txt' % py_version)
        target_files.append('test-requirements-py%s.txt' % py_version)
    for target_file in target_files:
        _safe_read(result, target_file, output=requirements)
    return result


def _write_project(project, actions, stdout, verbose):
    """Write actions into project.

    :param project: A project metadata dict.
    :param actions: A list of action tuples - File or Verbose - that describe
        what actions are to be taken.
        File objects describe a file to have content placed in it.
        StdOut objects describe a messge to write to stdout.
        Verbose objects will write a message to stdout when verbose is True.
    :param stdout: Where to write content for stdout.
    :param verbose: If True Verbose actions will be written to stdout.
    :return None:
    :raises IOError: If the IO operations fail, IOError is raised. If this
        happens some actions may have been applied and others not.
    """
    for action in actions:
        if type(action) is File:
            with open(project['root'] + '/' + action.filename, 'wt') as f:
                f.write(action.content)
        elif type(action) is StdOut:
            stdout.write(action.message)
        elif type(action) is Verbose:
            if verbose:
                stdout.write(u"%s\n" % (action.message,))
        else:
            raise Exception("Invalid action %r" % (action,))


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
        reqs[_package_name(pip)] = pip
    return reqs


def main(argv=None, stdout=None, _worker=None):
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output-suffix", dest="suffix", default="",
                      help="output suffix for updated files (i.e. .global)")
    parser.add_option("-s", "--soft-update", dest="softupdate",
                      action="store_true",
                      help="Pass through extra requirements without warning.")
    parser.add_option("-H", "--hacking", dest="hacking",
                      action="store_true",
                      help="Include the hacking project.")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true",
                      help="Add further verbosity to output")
    parser.add_option("--source", dest="source", default=".",
                      help="Dir where global-requirements.txt is located.")
    options, args = parser.parse_args(argv)
    if len(args) != 1:
        print("Must specify directory to update")
        raise Exception("Must specify one and only one directory to update.")
    if stdout is None:
        stdout = sys.stdout
    if _worker is None:
        _worker = _do_main
    non_std_reqs = os.getenv('NON_STANDARD_REQS', '0') == '1'
    _worker(
        args[0], options.source, options.suffix, options.softupdate,
        options.hacking, stdout, options.verbose, non_std_reqs)


def _do_main(
        root, source, suffix, softupdate, hacking, stdout, verbose,
        non_std_reqs):
    """No options or environment variable access from here on in."""
    project = _read_project(root)
    global_reqs = _parse_reqs(
        os.path.join(source, 'global-requirements.txt'))
    actions = _process_project(
        project, global_reqs, suffix, softupdate, hacking, non_std_reqs)
    _write_project(project, actions, stdout=stdout, verbose=verbose)


if __name__ == "__main__":
    main()
