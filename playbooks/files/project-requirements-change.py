#! /usr/bin/env python
# Copyright (C) 2011 OpenStack, LLC.
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import collections
import contextlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile


requirement = None
project = None


def run_command(cmd):
    print(cmd)
    cmd_list = shlex.split(str(cmd))
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise SystemError(err)
    return (out.strip(), err.strip())


class RequirementsList(object):
    def __init__(self, name, project):
        self.name = name
        self.reqs_by_file = {}
        self.project = project
        self.failed = False

    @property
    def reqs(self):
        return {k: v for d in self.reqs_by_file.values()
                for k, v in d.items()}

    def extract_reqs(self, content, strict):
        reqs = collections.defaultdict(set)
        parsed = requirement.parse(content)
        for name, entries in parsed.items():
            if not name:
                # Comments and other unprocessed lines
                continue
            list_reqs = [r for (r, line) in entries]
            # Strip the comments out before checking if there are duplicates
            list_reqs_stripped = [r._replace(comment='') for r in list_reqs]
            if strict and len(list_reqs_stripped) != len(set(
                    list_reqs_stripped)):
                print("Requirements file has duplicate entries "
                      "for package %s : %r." % (name, list_reqs))
                self.failed = True
            reqs[name].update(list_reqs)
        return reqs

    def process(self, strict=True):
        """Convert the project into ready to use data.

        - an iterable of requirement sets to check
        - each set has the following rules:
          - each has a list of Requirements objects
          - duplicates are not permitted within that list
        """
        print("Checking %(name)s" % {'name': self.name})
        # First, parse.
        for fname, content in self.project.get('requirements', {}).items():
            print("Processing %(fname)s" % {'fname': fname})
            if strict and not content.endswith('\n'):
                print("Requirements file %s does not "
                      "end with a newline." % fname)
            self.reqs_by_file[fname] = self.extract_reqs(content, strict)

        for name, content in project.extras(self.project).items():
            print("Processing .[%(extra)s]" % {'extra': name})
            self.reqs_by_file[name] = self.extract_reqs(content, strict)


def grab_args():
    """Grab and return arguments"""
    parser = argparse.ArgumentParser(
        description="Check if project requirements have changed"
    )
    parser.add_argument('--local', action='store_true',
                        help='check local changes (not yet in git)')
    parser.add_argument('branch', nargs='?', default='master',
                        help='target branch for diffs')
    parser.add_argument('--zc', help='what zuul cloner to call')
    parser.add_argument('--reqs', help='use a specified requirements tree')

    return parser.parse_args()


@contextlib.contextmanager
def tempdir():
    try:
        reqroot = tempfile.mkdtemp()
        yield reqroot
    finally:
        shutil.rmtree(reqroot)


def install_and_load_requirements(reqroot, reqdir):
    sha = run_command("git --git-dir %s/.git rev-parse HEAD" % reqdir)[0]
    print("requirements git sha: %s" % sha)
    req_venv = os.path.join(reqroot, 'venv')
    req_pip = os.path.join(req_venv, 'bin/pip')
    req_lib = os.path.join(req_venv, 'lib/python2.7/site-packages')
    out, err = run_command("virtualenv " + req_venv)
    out, err = run_command(req_pip + " install " + reqdir)
    sys.path.append(req_lib)
    global project
    global requirement
    from openstack_requirements import project  # noqa
    from openstack_requirements import requirement  # noqa


def _is_requirement_in_global_reqs(req, global_reqs):
    # Compare all fields except the extras field as the global
    # requirements should not have any lines with the extras syntax
    # example: oslo.db[xyz]<1.2.3
    for req2 in global_reqs:
        if (req.package == req2.package and
           req.location == req2.location and
           req.specifiers == req2.specifiers and
           req.markers == req2.markers and
           req.comment == req2.comment):
            return True
    return False


def main():
    args = grab_args()
    branch = args.branch
    failed = False

    # build a list of requirements from the global list in the
    # openstack/requirements project so we can match them to the changes
    reqdir = os.path.expanduser(
        '~/src/git.openstack.org/openstack/requirements')
    with tempdir() as reqroot:

        install_and_load_requirements(reqroot, reqdir)
        global_reqs = requirement.parse(
            open(reqdir + '/global-requirements.txt', 'rt').read())
        for k, entries in global_reqs.items():
            # Discard the lines: we don't need them.
            global_reqs[k] = set(r for (r, line) in entries)
        blacklist = requirement.parse(
            open(reqdir + '/blacklist.txt', 'rt').read())
        cwd = os.getcwd()
        # build a list of requirements in the proposed change,
        # and check them for style violations while doing so
        head = run_command("git rev-parse HEAD")[0]
        head_proj = project.read(cwd)
        head_reqs = RequirementsList('HEAD', head_proj)
        # Don't apply strict parsing rules to stable branches.
        # Reasoning is:
        #  - devstack etc protect us from functional issues
        #  - we're backporting to stable, so guarding against
        #    aesthetics and DRY concerns is not our business anymore
        #  - if in future we have other not-functional linty style
        #    things to add, we don't want them to affect stable
        #    either.
        head_strict = not branch.startswith('stable/')
        head_reqs.process(strict=head_strict)

        if not args.local:
            # build a list of requirements already in the target branch,
            # so that we can create a diff and identify what's being changed
            run_command("git checkout %s" % branch)
            branch_proj = project.read(cwd)

            # switch back to the proposed change now
            run_command("git checkout %s" % head)
        else:
            branch_proj = {'root': cwd}
        branch_reqs = RequirementsList(branch, branch_proj)
        # Don't error on the target branch being broken.
        branch_reqs.process(strict=False)

        # iterate through the changing entries and see if they match the global
        # equivalents we want enforced
        for fname, freqs in head_reqs.reqs_by_file.items():
            print("Validating %(fname)s" % {'fname': fname})
            for name, reqs in freqs.items():
                counts = {}
                if (name in branch_reqs.reqs and
                   reqs == branch_reqs.reqs[name]):
                    # Unchanged [or a change that preserves a current value]
                    continue
                if name in blacklist:
                    # Blacklisted items are not synced and are managed
                    # by project teams as they see fit, so no further
                    # testing is needed.
                    continue
                if name not in global_reqs:
                    failed = True
                    print("Requirement %s not in openstack/requirements" %
                          str(reqs))
                    continue
                if reqs == global_reqs[name]:
                    continue
                for req in reqs:
                    if req.extras:
                        for extra in req.extras:
                            counts[extra] = counts.get(extra, 0) + 1
                    else:
                        counts[''] = counts.get('', 0) + 1
                    if not _is_requirement_in_global_reqs(
                            req, global_reqs[name]):
                        failed = True
                        print("Requirement for package %s : %s does "
                              "not match openstack/requirements value : %s" % (
                                  name, str(req), str(global_reqs[name])))
                for extra, count in counts.items():
                    if count != len(global_reqs[name]):
                        failed = True
                        print("Package %s%s requirement does not match "
                              "number of lines (%d) in "
                              "openstack/requirements" % (
                                  name,
                                  ('[%s]' % extra) if extra else '',
                                  len(global_reqs[name])))

    # report the results
    if failed or head_reqs.failed or branch_reqs.failed:
        print("*** Incompatible requirement found!")
        print("*** See http://docs.openstack.org/developer/requirements")
        sys.exit(1)
    print("Updated requirements match openstack/requirements.")


if __name__ == '__main__':
    main()
