#! /usr/bin/env python3
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
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

from openstack_requirements import check  # noqa
from openstack_requirements import project  # noqa
from openstack_requirements import requirement  # noqa


PYTHON_3_BRANCH = re.compile(r'^stable\/[u-z].*')


def run_command(cmd):
    print(cmd)
    cmd_list = shlex.split(str(cmd))
    kwargs = {}
    if sys.version_info >= (3, ):
        kwargs = {
            'encoding': 'utf-8',
            'errors': 'surrogateescape',
        }
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, **kwargs)
    (out, err) = p.communicate()
    if p.returncode != 0:
        raise SystemError(err)
    return (out.strip(), err.strip())


_DEFAULT_REQS_DIR = os.path.expanduser(
    '~/src/opendev.org/openstack/requirements')


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
                        default=None)

    return parser.parse_args()


@contextlib.contextmanager
def tempdir():
    try:
        reqroot = tempfile.mkdtemp()
        yield reqroot
    finally:
        shutil.rmtree(reqroot)


def main():
    args = grab_args()
    branch = args.branch
    reqdir = args.reqs

    print(sys.version_info)

    if reqdir is None:
        if args.local:
            print('selecting default requirements directory for local mode')
            reqdir = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(sys.argv[0]))))
        else:
            print('selecting default requirements directory for normal mode')
            reqdir = _DEFAULT_REQS_DIR

    print('Branch: {}'.format(branch))
    print('Source: {}'.format(args.src_dir))
    print('Requirements: {}'.format(reqdir))

    os.chdir(args.src_dir)
    sha, _ = run_command('git log -n 1 --format=%H')
    print('Patch under test: {}'.format(sha))

    # build a list of requirements from the global list in the
    # openstack/requirements project so we can match them to the changes
    with tempdir():
        with open(reqdir + '/global-requirements.txt', 'rt') as f:
            global_reqs = check.get_global_reqs(f.read())
        blacklist = requirement.parse(
            open(reqdir + '/blacklist.txt', 'rt').read())
        cwd = os.getcwd()
        # build a list of requirements in the proposed change,
        # and check them for style violations while doing so
        head_proj = project.read(cwd)
        head_reqs = check.RequirementsList(sha, head_proj)
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
        # Starting with Ussuri and later, we only need to be strict about
        # Python 3 requirements.
        python_3_branch = head_strict or PYTHON_3_BRANCH.match(branch)

        failed = check.validate(
            head_reqs,
            blacklist,
            global_reqs,
            allow_3_only=python_3_branch,
        )

        failed = (
            check.validate_lower_constraints(
                head_reqs,
                head_proj['lower-constraints.txt'],
                blacklist,
            )
            or failed
        )

    # report the results
    if failed or head_reqs.failed:
        print("*** Incompatible requirement found!")
        print("*** See https://docs.openstack.org/requirements/latest/")
        sys.exit(1)
    print("Updated requirements match openstack/requirements.")


if __name__ == '__main__':
    main()
