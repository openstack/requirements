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
import contextlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile


requirement = None
project = None
check = None


def run_command(cmd):
    print(cmd)
    cmd_list = shlex.split(str(cmd))
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise SystemError(err)
    return (out.strip(), err.strip())


def grab_args():
    """Grab and return arguments"""
    parser = argparse.ArgumentParser(
        description="Check if project requirements have changed"
    )
    parser.add_argument('--local', action='store_true',
                        help='check local changes (not yet in git)')
    parser.add_argument('src_dir', help='directory to process')
    parser.add_argument('branch', nargs='?', default='master',
                        help='target branch for diffs')
    parser.add_argument('--zc', help='what zuul cloner to call')
    parser.add_argument('--reqs', help='use a specified requirements tree',
                        default=os.path.expanduser(
                            '~/src/git.openstack.org/openstack/requirements'))

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
    global check
    global project
    global requirement
    from openstack_requirements import check  # noqa
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
    os.chdir(args.src_dir)
    reqdir = args.reqs

    # build a list of requirements from the global list in the
    # openstack/requirements project so we can match them to the changes
    with tempdir() as reqroot:

        install_and_load_requirements(reqroot, reqdir)
        with open(reqdir + '/global-requirements.txt', 'rt') as f:
            global_reqs = check.get_global_reqs(f.read())
        blacklist = requirement.parse(
            open(reqdir + '/blacklist.txt', 'rt').read())
        cwd = os.getcwd()
        # build a list of requirements in the proposed change,
        # and check them for style violations while doing so
        head_proj = project.read(cwd)
        head_reqs = check.RequirementsList('HEAD', head_proj)
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
            run_command("git checkout HEAD^1")
            branch_proj = project.read(cwd)

            # switch back to the proposed change now
            run_command("git checkout %s" % branch)
        else:
            branch_proj = {'root': cwd}
        branch_reqs = check.RequirementsList(branch, branch_proj)
        # Don't error on the target branch being broken.
        branch_reqs.process(strict=False)

        failed = check.validate(head_reqs, branch_reqs, blacklist, global_reqs)

        failed = (
            check.validate_lower_constraints(
                head_reqs,
                head_proj['lower_constraints.txt'],
                blacklist,
            )
            or failed
        )

    # report the results
    if failed or head_reqs.failed or branch_reqs.failed:
        print("*** Incompatible requirement found!")
        print("*** See http://docs.openstack.org/developer/requirements")
        sys.exit(1)
    print("Updated requirements match openstack/requirements.")


if __name__ == '__main__':
    main()
