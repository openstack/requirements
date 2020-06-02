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

import contextlib
import json
import os
import six.moves.urllib.parse as urlparse
import six.moves.urllib.request as urlreq
import sys
import traceback

import pkg_resources

try:
    PYPI_LOCATION = os.environ['PYPI_LOCATION']
except KeyError:
    PYPI_LOCATION = 'http://pypi.org/project'


KEEP_KEYS = frozenset([
    'author',
    'author_email',
    'maintainer',
    'maintainer_email',
    'license',
    'summary',
    'home_page',
])


def iter_names(req):
    for k in (req.key, req.project_name):
        yield k
        yield k.title()
        yield k.replace("-", "_")
        yield k.replace("-", "_").title()


def release_data(req):
    # Try to find it with various names...
    attempted = []
    for name in iter_names(req):
        url = PYPI_LOCATION + "/%s/json" % (urlparse.quote(name))
        if url in attempted:
            continue
        with contextlib.closing(urlreq.urlopen(url)) as uh:
            if uh.getcode() != 200:
                attempted.append(url)
                continue
            return json.loads(uh.read())
    attempted = [" * %s" % u for u in attempted]
    raise IOError("Could not find '%s' on pypi\nAttempted urls:\n%s"
                  % (req.key, "\n".join(attempted)))


def main():
    if len(sys.argv) == 1:
        print("%s requirement-file ..." % (sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    for filename in sys.argv[1:]:
        print("Analyzing file: %s" % (filename))
        details = {}
        with open(filename, "rb") as fh:
            for line in fh.read().splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                req = pkg_resources.Requirement.parse(line)
                print(" - processing: %s" % (req))
                try:
                    raw_req_data = release_data(req)
                except IOError:
                    traceback.print_exc()
                    details[req.key] = None
                else:
                    req_info = {}
                    for (k, v) in raw_req_data.get('info', {}).items():
                        if k not in KEEP_KEYS:
                            continue
                        req_info[k] = v
                    details[req.key] = {
                        'requirement': str(req),
                        'info': req_info,
                    }
        filename, _ext = os.path.splitext(filename)
        with open("%s.json" % (filename), "wb") as fh:
            fh.write(json.dumps(details, sort_keys=True, indent=4,
                                separators=(",", ": ")))


if __name__ == '__main__':
    main()
