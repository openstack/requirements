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

from __future__ import print_function

import argparse

import pkg_resources
import requests


_url_template = 'https://pypi.org/project/{dist}/{version}/json'


def _get_metadata(dist, version):
    try:
        url = _url_template.format(dist=dist, version=version)
        response = requests.get(url)
        return response.json()
    except ValueError:
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--verbose', '-v',
        default=False,
        action='store_true',
        help='turn on noisy output',
    )
    parser.add_argument(
        '--requirements',
        default='upper-constraints.txt',
        help='the list of constrained requirements to check',
    )
    args = parser.parse_args()

    for line in open(args.requirements, 'r'):
        try:
            req = pkg_resources.Requirement.parse(line)
        except ValueError:
            # Assume this is a comment and skip it.
            continue
        # req.specifier is a set so we can't get an item out of it
        # directly. Turn it into a list and take the first (and only)
        # value. That gives us an _IndividualSpecifier which has a
        # version attribute that is not smart enough to filter out the
        # selector value for things like python version, so drop
        # anything after the first semicolon.
        version = list(req.specifier)[0].version.split(';')[0]
        data = _get_metadata(req.project_name, version)
        classifiers = data.get('info', {}).get('classifiers', [])
        for classifier in classifiers:
            if classifier.startswith('Programming Language :: Python :: 2'):
                if args.verbose:
                    print('{}==={} {!r}'.format(
                        req.project_name, version, classifier))
                break
        else:
            print('\nNo "Python :: 2" classifier found for {}==={}'.format(
                req.project_name, version))
            for classifier in classifiers:
                print('  {}'.format(classifier))

if __name__ == '__main__':
    main()
