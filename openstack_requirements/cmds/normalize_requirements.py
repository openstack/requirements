#! /usr/bin/env python

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
import os.path

from openstack_requirements import requirement


def write_requirements_file(filename, reqs):
    with open(filename + 'tmp', 'wt') as f:
        f.write(reqs)
    if os.path.exists(filename):
        os.remove(filename)
    os.rename(filename + 'tmp', filename)


def main():
    parser = argparse.ArgumentParser(
        description="Normalize requirements files")
    parser.add_argument('requirements', help='requirements file input')
    parser.add_argument('-s', '--save', action='store_true', default=False,
                        help=('save normalized requirements '
                              'file instead of displaying it'))
    args = parser.parse_args()
    with open(args.requirements) as f:
        requirements = [line.strip() for line in f.readlines()]

    normed_reqs = ""
    for line in requirements:
        req = requirement.parse_line(line)
        normed_req = req.to_line(comment_prefix='  ', sort_specifiers=True)
        normed_reqs += normed_req

    if args.save:
        write_requirements_file(args.requirements, normed_reqs)
    else:
        print(normed_reqs, end='')


if __name__ == '__main__':
    main()
