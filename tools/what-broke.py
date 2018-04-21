#!/usr/bin/python
#
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""what-broke.py - figure out what requirements change likely broke us.

Monday morning, 6am. Loading up zuul status page, and realize there is
a lot of red in the gate. Get second cup of coffee. Oh, some library
must have released a bad version. Man, what released recently?

This script attempts to give that answer by programmatically providing
a list of everything in global-requirements that released recently, in
descending time order.

This does *not* handle the 2nd order dependency problem (in order to
do that we'd have to install the world as well, this is purely a
metadata lookup tool). If we have regularly problematic 2nd order
dependencies add them to the list at the end in the code to be
checked.

"""

import argparse
import datetime
import json
import six.moves.urllib.request as urlreq
import sys

import pkg_resources


class Release(object):
    name = ""
    version = ""
    filename = ""
    released = ""

    def __init__(self, name, version, filename, released):
        self.name = name
        self.version = version
        self.filename = filename
        self.released = released

    def __repr__(self):
        return "<Released %s %s %s>" % (self.name, self.version, self.released)


def _parse_pypi_released(datestr):
    return datetime.datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S")


def _package_name(line):
    return pkg_resources.Requirement.parse(line).project_name


def get_requirements():
    reqs = []
    with open('global-requirements.txt') as f:
        for line in f.readlines():
            # skip the comment or empty lines
            if not line or line.startswith(('#', '\n')):
                continue
            # get rid of env markers, they are not relevant for our purposes.
            line = line.split(';')[0]
            reqs.append(_package_name(line))
    return reqs


def get_releases_for_package(name, since):

    """Get the release history from pypi

    Use the json API to get the release history from pypi. The
    returned json structure includes a 'releases' dictionary which has
    keys that are release numbers and the value is an array of
    uploaded files.

    While we don't have a 'release time' per say (only the upload time
    on each of the files), we'll consider the timestamp on the first
    source file found (which will be a .zip or tar.gz typically) to be
    'release time'. This is inexact, but should be close enough for
    our purposes.

    """
    f = urlreq.urlopen("http://pypi.org/project/%s/json" % name)
    jsondata = f.read()
    data = json.loads(jsondata)
    releases = []
    for relname, rellist in data['releases'].iteritems():
        for rel in rellist:
            if rel['python_version'] == 'source':
                when = _parse_pypi_released(rel['upload_time'])
                # for speed, only care about when > since
                if when < since:
                    continue

                releases.append(
                    Release(
                        name,
                        relname,
                        rel['filename'],
                        when))
                break
    return releases


def get_releases_since(reqs, since):
    all_releases = []
    for req in reqs:
        all_releases.extend(get_releases_for_package(req, since))
    # return these in a sorted order from newest to oldest
    sorted_releases = sorted(all_releases,
                             key=lambda x: x.released,
                             reverse=True)
    return sorted_releases


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            'List recent releases of items in global requirements '
            'to look for possible breakage'))
    parser.add_argument('-s', '--since', type=int,
                        default=14,
                        help='look back ``since`` days (default 14)')
    return parser.parse_args()


def main():
    opts = parse_args()
    since = datetime.datetime.today() - datetime.timedelta(days=opts.since)
    print("Looking for requirements releases since %s" % since)
    reqs = get_requirements()
    # additional sensitive requirements
    reqs.append('tox')
    reqs.append('pycparser')
    releases = get_releases_since(reqs, since)
    for rel in releases:
        print(rel)


if __name__ == '__main__':
    sys.exit(main())
