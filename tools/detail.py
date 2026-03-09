#    Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# Script to extract detailed package information from PyPi for all entries in
# a requirements file. JSON formatted details are written to a *.json file
# corresponding to the input file. As an example, the following command:
#
# python3 detail.py global-requirements.txt
#
# would result in a 'global-requirements.json' file containing an entry for
# each requirement.

import contextlib
import json
import os
import sys
import traceback
import urllib.parse as urlparse
import urllib.request as urlreq

import packaging.requirements

try:
    PYPI_LOCATION = os.environ['PYPI_LOCATION']
except KeyError:
    PYPI_LOCATION = 'https://pypi.org/pypi'


KEEP_KEYS = frozenset(
    [
        'author',
        'author_email',
        'maintainer',
        'maintainer_email',
        'license',
        'summary',
        'home_page',
    ]
)


def iter_names(req):
    yield req.name
    yield req.name.lower()
    yield req.name.title()
    yield req.name.replace("-", "_")
    yield req.name.replace("-", "_").title()


def release_data(req):
    # Try to find it with various names...
    attempted = []
    for name in iter_names(req):
        url = PYPI_LOCATION + f"/{urlparse.quote(name)}/json"
        if url in attempted:
            continue
        req_obj = urlreq.Request(url, headers={'User-Agent': 'detail.py/1.0'})
        with contextlib.closing(urlreq.urlopen(req_obj)) as uh:
            if uh.getcode() != 200:
                attempted.append(url)
                continue
            return json.loads(uh.read())
    attempted = [f" * {u}" for u in attempted]
    raise OSError(
        "Could not find '{}' on pypi\nAttempted urls:\n{}".format(
            req.key, "\n".join(attempted)
        )
    )


def main():
    if len(sys.argv) == 1:
        print(f"{sys.argv[0]} requirement-file ...", file=sys.stderr)
        sys.exit(1)
    for filename in sys.argv[1:]:
        print(f"Analyzing file: {filename}")
        details = {}
        with open(filename) as fh:
            for line in fh.read().splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                req = packaging.requirements.Requirement(
                    line.partition('#')[0].strip()
                )
                print(f" - processing: {req}")
                try:
                    raw_req_data = release_data(req)
                except OSError:
                    traceback.print_exc()
                    details[req.key] = None
                else:
                    req_info = {}
                    for k, v in raw_req_data.get('info', {}).items():
                        if k not in KEEP_KEYS:
                            continue
                        req_info[k] = v
                    details[req.name] = {
                        'requirement': str(req),
                        'info': req_info,
                    }
        filename, _ext = os.path.splitext(filename)
        with open(f"{filename}.json", "w") as fh:
            fh.write(
                json.dumps(
                    details, sort_keys=True, indent=4, separators=(",", ": ")
                )
            )


if __name__ == '__main__':
    main()
