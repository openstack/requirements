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

import collections
import re
import sys

from packaging import markers

from openstack_requirements import requirement

MIN_PY_VERSION = '3.5'
PY3_GLOBAL_SPECIFIER_RE = re.compile(
    r'python_version(==|>=|>)[\'"]3\.\d+[\'"]'
)
PY3_LOCAL_SPECIFIER_RE = re.compile(
    r'python_version(==|>=|>|<=|<)[\'"]3\.\d+[\'"]'
)


class RequirementsList:
    def __init__(self, name, project):
        self.name = name
        self.reqs_by_file = {}
        self.project = project
        self.failed = False

    @property
    def reqs(self):
        return {k: v for d in self.reqs_by_file.values() for k, v in d.items()}

    def extract_reqs(self, content, strict):
        reqs = collections.defaultdict(set)
        parsed = requirement.parse_lines(content)
        for name, entries in parsed.items():
            if not name:
                # Comments and other unprocessed lines
                continue
            list_reqs = [r for (r, line) in entries]
            # Strip the comments out before checking if there are duplicates
            list_reqs_stripped = [r._replace(comment='') for r in list_reqs]
            if strict and len(list_reqs_stripped) != len(
                set(list_reqs_stripped)
            ):
                print(
                    f"ERROR: Requirements file has duplicate entries "
                    f"for package {name} : {list_reqs!r}.",
                    file=sys.stderr,
                )
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
        print(f"Checking {self.name}")
        for fname, content in self.project['requirements'].items():
            if (
                fname
                in {
                    'tools/pip-requires',
                    'tools/test-requires',
                    'requirements-py2.txt',
                    'requirements-py3.txt',
                    'test-requirements-py2.txt',
                    'test-requirements-py3.txt',
                }
                and content
            ):
                # TODO(stephenfin): Make this an error in the H cycle (mid
                # 2026). These files are all obsolete and pbr no longer
                # supported the pyN-suffixed files (since pbr 5.0) and never
                # supported the *-requires files
                print(
                    "WARNING: Requirements file {fname} is non-standard "
                    "and will cause an error in the future. "
                    "Use a pyproject.toml or requirements.txt / "
                    "test-requirements.txt file instead.",
                    file=sys.stderr,
                )

            print(f"Processing {fname} (requirements)")
            if strict and not content.endswith('\n'):
                print(
                    f"Requirements file {fname} does not end with a newline.",
                    file=sys.stderr,
                )
            self.reqs_by_file[fname] = self.extract_reqs(content, strict)

        for fname, extras in self.project['extras'].items():
            print(f"Processing {fname} (extras)")
            for name, content in extras.items():
                print(f"Processing .[{name}]")
                self.reqs_by_file[name] = self.extract_reqs(content, strict)


def _get_exclusions(req):
    return set(
        spec
        for spec in req.specifiers.split(',')
        if '!=' in spec or '<' in spec
    )


def _is_requirement_in_global_reqs(
    local_req,
    global_reqs,
    backports,
    allow_3_only=False,
):
    req_exclusions = _get_exclusions(local_req)
    for global_req in global_reqs:
        matching = True
        for aname in ['package', 'location', 'markers']:
            local_req_val = getattr(local_req, aname)
            global_req_val = getattr(global_req, aname)
            if local_req_val != global_req_val:
                # if a python 3 version is not spefied in only one of
                # global requirements or local requirements, allow it since
                # python 3-only is okay
                if allow_3_only and matching and aname == 'markers':
                    if not local_req_val and PY3_GLOBAL_SPECIFIER_RE.match(
                        global_req_val
                    ):
                        continue
                    if (
                        not global_req_val
                        and local_req_val
                        and PY3_LOCAL_SPECIFIER_RE.match(local_req_val)
                    ):
                        continue

                # likewise, if a package is one of the backport packages then
                # we're okay with a potential marker (e.g. if a package
                # requires a feature that is only available in a newer Python
                # library, while other packages are happy without this feature
                if (
                    matching
                    and aname == 'markers'
                    and local_req.package in backports
                ):
                    if re.match(
                        r'python_version(==|<=|<)[\'"]3\.\d+[\'"]',
                        local_req_val,
                    ):
                        print(
                            'Ignoring backport package with python_version '
                            'marker'
                        )
                        continue

                print(
                    f'WARNING: possible mismatch found for package "{local_req.package}"'
                )  # noqa: E501
                print(f'   Attribute "{aname}" does not match')
                print(
                    f'   "{local_req_val}" does not match "{global_req_val}"'
                )  # noqa: E501
                print(f'   {local_req}')
                print(f'   {global_req}')
                matching = False
        if not matching:
            continue

        # This matches the right package and other properties, so
        # ensure that any exclusions are a subset of the global
        # set.
        global_exclusions = _get_exclusions(global_req)
        if req_exclusions.issubset(global_exclusions):
            return True
        else:
            difference = req_exclusions - global_exclusions
            print(
                f"ERROR: Requirement for package {local_req.package} "
                "excludes a version not excluded in the "
                "global list.\n"
                f"  Local settings : {req_exclusions}\n"
                f"  Global settings: {global_exclusions}\n"
                f"  Unexpected     : {difference}"
            )
            return False

    print(
        "ERROR: "
        f"Could not find a global requirements entry to match package {local_req.package}. "
        "If the package is already included in the global list, "
        "the name or platform markers there may not match the local "
        "settings."
    )
    return False


def get_global_reqs(content):
    """Return global_reqs structure.

    Parse content and return dict mapping names to sets of Requirement
    objects."

    """
    global_reqs = {}
    parsed = requirement.parse(content)
    for k, entries in parsed.items():
        # Discard the lines: we don't need them.
        global_reqs[k] = set(r for (r, line) in entries)
    return global_reqs


def _get_python3_reqs(reqs):
    """Filters out the reqs that are less than our minimum version."""
    results = []
    for req in reqs:
        if not req.markers:
            results.append(req)
        else:
            req_markers = markers.Marker(req.markers)
            if req_markers.evaluate(
                {
                    'python_version': MIN_PY_VERSION,
                }
            ):
                results.append(req)
    return results


def _validate_one(
    name,
    reqs,
    denylist,
    global_reqs,
    backports,
    allow_3_only=False,
):
    """Returns True if there is a failure."""

    if name in denylist:
        # Denylisted items are not synced and are managed
        # by project teams as they see fit, so no further
        # testing is needed.
        return False

    if name not in global_reqs:
        print(f"ERROR: Requirement '{reqs}' not in openstack/requirements")
        return True

    counts = {}
    for req in reqs:
        if req.extras:
            for extra in req.extras:
                counts[extra] = counts.get(extra, 0) + 1
        else:
            counts[''] = counts.get('', 0) + 1

        if not _is_requirement_in_global_reqs(
            req,
            global_reqs[name],
            backports,
            allow_3_only,
        ):
            return True

        # check for minimum being defined
        min = [s for s in req.specifiers.split(',') if '>' in s]
        if not min:
            print(
                f"ERROR: Requirement for package '{name}' has no lower bound"
            )
            return True

    for extra, count in counts.items():
        # Make sure the number of entries matches. If allow_3_only, then we
        # just need to make sure we have at least the number of entries for
        # supported Python 3 versions.
        if count != len(global_reqs[name]):
            if allow_3_only and count >= len(
                _get_python3_reqs(global_reqs[name])
            ):
                print(
                    "WARNING (probably OK for Ussuri and later): "
                    "Package '{}{}' is only tracking python 3 "
                    "requirements".format(
                        name, (f'[{extra}]') if extra else ''
                    )
                )
                continue

            print(
                "ERROR: Package '{}{}' requirement does not match "
                "number of lines ({}) in "
                "openstack/requirements".format(
                    name,
                    (f'[{extra}]') if extra else '',
                    len(global_reqs[name]),
                )
            )
            return True

    return False


def validate(
    head_reqs,
    denylist,
    global_reqs,
    backports,
    allow_3_only=False,
):
    failed = False
    # iterate through the changing entries and see if they match the global
    # equivalents we want enforced
    for fname, freqs in head_reqs.reqs_by_file.items():
        print(f"Validating {fname}")
        for name, reqs in freqs.items():
            failed = (
                _validate_one(
                    name,
                    reqs,
                    denylist,
                    global_reqs,
                    backports,
                    allow_3_only,
                )
                or failed
            )

    return failed
