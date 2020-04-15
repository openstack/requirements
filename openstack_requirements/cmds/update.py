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

import optparse
import os
import os.path
import sys

import six

from openstack_requirements import project
from openstack_requirements import requirement

_setup_py_text = """# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
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
    setup_requires=['pbr>=2.0.0'],
    pbr=True)
"""


# Pure --

class Change(object):
    def __init__(self, name, old, new):
        self.name = name
        self.old = old.strip()
        self.new = new.strip()

    def __repr__(self):
        return "%-30.30s ->   %s" % (self.old, self.new)


def _check_setup_py(proj):
    actions = []
    # If it doesn't have a setup.py, then we don't want to update it
    if 'setup.py' not in proj:
        return actions
    # If it doesn't use pbr, we don't want to update it.
    elif 'pbr' not in proj['setup.py']:
        return actions
    # We don't update pbr's setup.py because it can't use itself.
    if 'setup.cfg' in proj and 'name = pbr' in proj['setup.cfg']:
        return actions
    actions.append(project.Verbose("Syncing setup.py"))
    actions.append(project.File('setup.py', _setup_py_text))
    return actions


def _sync_requirements_file(
        source_reqs, dest_sequence, dest_label, softupdate, hacking,
        non_std_reqs, blacklist={}):
    actions = []
    dest_reqs = requirement.to_dict(dest_sequence)
    changes = []
    output_requirements = []
    processed_packages = set()

    for req, req_line in dest_sequence:
        # Skip the instructions header
        if req_line in requirement._REQS_HEADER:
            continue
        elif req is None:
            # Unparsable lines.
            output_requirements.append(
                requirement.Requirement('', '', '', '', req_line.rstrip()))
            continue
        elif not req.package:
            # Comment-only lines
            output_requirements.append(req)
            continue
        elif req.package.lower() in processed_packages:
            continue

        processed_packages.add(req.package.lower())
        # Special cases:
        # projects need to align hacking version on their own time
        if req.package == "hacking" and not hacking:
            output_requirements.append(req)
            continue
        # the overall blacklist is similarly synced by projects as
        # needed
        if req.package in blacklist:
            output_requirements.append(req)
            continue

        reference = source_reqs.get(req.package.lower())
        if reference:
            actual = dest_reqs.get(req.package.lower())
            for req, ref in six.moves.zip_longest(actual, reference):
                if not req:
                    # More in globals
                    changes.append(Change(ref[0].package, '', ref[1]))
                elif not ref:
                    # less in globals
                    changes.append(Change(req[0].package, req[1], ''))
                elif req[0] != ref[0]:
                    # NOTE(jamielennox): extras are allowed to be specified in
                    # a project's requirements and the version be updated and
                    # extras maintained. Create a new ref object the same as
                    # the original but with the req's extras.

                    merged_ref = requirement.Requirement(ref[0].package,
                                                         ref[0].location,
                                                         ref[0].specifiers,
                                                         ref[0].markers,
                                                         ref[0].comment,
                                                         req[0].extras)

                    ref = (merged_ref, merged_ref.to_line())

                    if req[0] != ref[0]:
                        # A change on this entry
                        changes.append(Change(req[0].package, req[1], ref[1]))

                if ref:
                    output_requirements.append(ref[0])
        elif softupdate:
            # under softupdate we pass through anything unknown packages,
            # this is intended for ecosystem projects that want to stay in
            # sync with existing requirements, but also add their own above
            # and beyond.
            output_requirements.append(req)
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
            # However this drops the unknown requirement.
            actions.append(project.Error(
                "'%s' is not in global-requirements.txt or blacklist.txt"
                % req.package))
    # always print out what we did if we did a thing
    if changes:
        actions.append(project.StdOut(
            "Version change for: %s\n"
            % ", ".join([x.name for x in changes])))
        actions.append(project.StdOut("Updated %s:\n" % dest_label))
        for change in changes:
            actions.append(project.StdOut("    %s\n" % change))
    return actions, requirement.Requirements(output_requirements)


def _copy_requires(
        suffix, softupdate, hacking, proj, global_reqs, non_std_reqs,
        blacklist={}):
    """Copy requirements files."""
    actions = []
    for source, content in sorted(proj['requirements'].items()):
        dest_path = os.path.join(proj['root'], source)
        # this is specifically for global-requirements gate jobs so we don't
        # modify the git tree
        if suffix:
            dest_path = "%s.%s" % (dest_path, suffix)
            dest_name = "%s.%s" % (source, suffix)
        else:
            dest_name = source
        dest_sequence = list(requirement.to_reqs(content))
        actions.append(project.Verbose("Syncing %s" % dest_path))
        _actions, reqs = _sync_requirements_file(
            global_reqs, dest_sequence, dest_path, softupdate, hacking,
            non_std_reqs, blacklist)
        actions.extend(_actions)
        actions.append(project.File(dest_name, requirement.to_content(reqs)))
    extras = project.extras(proj)
    output_extras = {}
    for extra, content in sorted(extras.items()):
        dest_name = 'extra-%s' % extra
        dest_path = "%s[%s]" % (proj['root'], extra)
        dest_sequence = list(requirement.to_reqs(content))
        actions.append(project.Verbose("Syncing extra [%s]" % extra))
        _actions, reqs = _sync_requirements_file(
            global_reqs, dest_sequence, dest_path, softupdate, hacking,
            non_std_reqs, blacklist)
        actions.extend(_actions)
        output_extras[extra] = reqs
    dest_path = 'setup.cfg'
    if suffix:
        dest_path = "%s.%s" % (dest_path, suffix)
    actions.append(project.File(
        dest_path, project.merge_setup_cfg(proj['setup.cfg'], output_extras)))
    return actions


def _process_project(
        project, global_reqs, suffix, softupdate, hacking, non_std_reqs,
        blacklist={}):
    """Project a project.

    :return: The actions to take as a result.
    """
    actions = _copy_requires(
        suffix, softupdate, hacking, project, global_reqs, non_std_reqs,
        blacklist)
    actions.extend(_check_setup_py(project))
    return actions


# IO --

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
    if not os.path.isdir(args[0]):
        print("%s is not a directory." % (args[0]))
        raise Exception("%s is not a directory." % (args[0]))
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
    proj = project.read(root)
    global_req_content = open(
        os.path.join(source, 'global-requirements.txt'), 'rt').read()
    global_reqs = requirement.parse(global_req_content)
    blacklist_content = open(
        os.path.join(source, 'blacklist.txt'), 'rt').read()
    blacklist = requirement.parse(blacklist_content)
    actions = _process_project(
        proj, global_reqs, suffix, softupdate, hacking, non_std_reqs,
        blacklist)
    project.write(proj, actions, stdout=stdout, verbose=verbose)


if __name__ == "__main__":
    main()
