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

from packaging import markers
from packaging import specifiers

from openstack_requirements import project
from openstack_requirements import requirement

MIN_PY_VERSION = '3.5'
PY3_SPECIFIER_RE = re.compile(r'python_version(==|>=|>)[\'"]3\.\d+[\'"]')


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
                print("ERROR: Requirements file has duplicate entries "
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


def _get_exclusions(req):
    return set(
        spec
        for spec in req.specifiers.split(',')
        if '!=' in spec or '<' in spec
    )


def _is_requirement_in_global_reqs(local_req, global_reqs, allow_3_only=False):
    req_exclusions = _get_exclusions(local_req)
    for global_req in global_reqs:

        matching = True
        for aname in ['package', 'location', 'markers']:
            local_req_val = getattr(local_req, aname)
            global_req_val = getattr(global_req, aname)
            if local_req_val != global_req_val:
                # if global requirements specifies a python 3 version specifier
                # but a project doesn't, allow it since python 3-only is okay
                if (allow_3_only and matching and
                        aname == 'markers' and not local_req_val):
                    if PY3_SPECIFIER_RE.match(global_req_val):
                        continue

                print('WARNING: possible mismatch found for package '
                      '"{}"'.format(local_req.package))
                print('   Attribute "{}" does not match'.format(aname))
                print('   "{}" does not match "{}"'.format(
                    local_req_val, global_req_val))
                print('   {}'.format(local_req))
                print('   {}'.format(global_req))
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
                "ERROR: Requirement for package {} "
                "excludes a version not excluded in the "
                "global list.\n"
                "  Local settings : {}\n"
                "  Global settings: {}\n"
                "  Unexpected     : {}".format(
                    local_req.package, req_exclusions, global_exclusions,
                    difference)
            )
            return False

    print(
        "ERROR: "
        "Could not find a global requirements entry to match package {}. "
        "If the package is already included in the global list, "
        "the name or platform markers there may not match the local "
        "settings.".format(local_req.package)
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
            if req_markers.evaluate({
                'python_version': MIN_PY_VERSION,
            }):
                results.append(req)
    return results


def _validate_one(name, reqs, blacklist, global_reqs, allow_3_only=False):
    """Returns True if there is a failure."""
    if name in blacklist:
        # Blacklisted items are not synced and are managed
        # by project teams as they see fit, so no further
        # testing is needed.
        return False
    if name not in global_reqs:
        print("ERROR: Requirement '%s' not in openstack/requirements" % reqs)
        return True
    counts = {}
    for req in reqs:
        if req.extras:
            for extra in req.extras:
                counts[extra] = counts.get(extra, 0) + 1
        else:
            counts[''] = counts.get('', 0) + 1
        if not _is_requirement_in_global_reqs(
                req, global_reqs[name], allow_3_only):
            return True
        # check for minimum being defined
        min = [s for s in req.specifiers.split(',') if '>' in s]
        if not min:
            print("ERROR: Requirement for package '%s' has no lower bound" %
                  name)
            return True
    for extra, count in counts.items():
        # Make sure the number of entries matches. If allow_3_only, then we
        # just need to make sure we have at least the number of entries for
        # supported Python 3 versions.
        if count != len(global_reqs[name]):
            if (allow_3_only and
                    count >= len(_get_python3_reqs(global_reqs[name]))):
                print("WARNING (probably OK for Ussuri and later): "
                      "Package '%s%s' is only tracking python 3 "
                      "requirements" % (
                        name,
                        ('[%s]' % extra) if extra else ''))
                continue

            print("ERROR: Package '%s%s' requirement does not match "
                  "number of lines (%d) in "
                  "openstack/requirements" % (
                      name,
                      ('[%s]' % extra) if extra else '',
                      len(global_reqs[name])))
            return True
    return False


def validate(head_reqs, blacklist, global_reqs, allow_3_only=False):
    failed = False
    # iterate through the changing entries and see if they match the global
    # equivalents we want enforced
    for fname, freqs in head_reqs.reqs_by_file.items():
        print("Validating %(fname)s" % {'fname': fname})
        for name, reqs in freqs.items():
            failed = (
                _validate_one(
                    name,
                    reqs,
                    blacklist,
                    global_reqs,
                    allow_3_only,
                )
                or failed
            )

    return failed


def _find_constraint(req, constraints):
    """Return the constraint matching the markers for req.

    Given a requirement, find the constraint with matching markers.
    If none match, find a constraint without any markers at all.
    Otherwise return None.
    """
    if req.markers:
        req_markers = markers.Marker(req.markers)
        for constraint_setting, _ in constraints:
            if constraint_setting.markers == req.markers:
                return constraint_setting
            if not constraint_setting.markers:
                # There is no point in performing the complex
                # comparison for a constraint that has no markers, so
                # we skip it here. If we find no closer match then the
                # loop at the end of the function will look for a
                # constraint without a marker and use that.
                continue
            # NOTE(dhellmann): This is a very naive attempt to check
            # marker compatibility that relies on internal
            # implementation details of the packaging library.  The
            # best way to ensure the constraint and requirements match
            # is to use the same marker string in the corresponding
            # lines.
            c_markers = markers.Marker(constraint_setting.markers)
            env = {
                str(var): str(val)
                for var, op, val in c_markers._markers  # WARNING: internals
            }
            if req_markers.evaluate(env):
                return constraint_setting
    # Try looking for a constraint without any markers.
    for constraint_setting, _ in constraints:
        if not constraint_setting.markers:
            return constraint_setting
    return None


def validate_lower_constraints(req_list, constraints, blacklist):
    """Return True if there is an error.

    :param reqs: RequirementsList for the head of the branch
    :param constraints: Parsed lower-constraints.txt or None

    """
    if constraints is None:
        return False

    parsed_constraints = requirement.parse(constraints)

    failed = False

    for fname, freqs in req_list.reqs_by_file.items():

        if fname == 'doc/requirements.txt':
            # Skip things that are not needed for unit or functional
            # tests.
            continue

        print("Validating lower constraints of {}".format(fname))

        for name, reqs in freqs.items():

            if name in blacklist:
                continue

            if name not in parsed_constraints:
                print('ERROR: Package {!r} is used in {} '
                      'but not in lower-constraints.txt'.format(
                          name, fname))
                failed = True
                continue

            for req in reqs:
                spec = specifiers.SpecifierSet(req.specifiers)
                # FIXME(dhellmann): This will only find constraints
                # where the markers match the requirements list
                # exactly, so we can't do things like use different
                # constrained versions for different versions of
                # python 3 if the requirement range is expressed as
                # python_version>3.0. We can support different
                # versions if there is a different requirement
                # specification for each version of python. I don't
                # really know how smart we want this to be, because
                # I'm not sure we want to support extremely
                # complicated dependency sets.
                constraint_setting = _find_constraint(
                    req,
                    parsed_constraints[name],
                )
                if not constraint_setting:
                    print('ERROR: Unable to find constraint for {} '
                          'matching {!r} or without any markers.'.format(
                              name, req.markers))
                    failed = True
                    continue

                version = constraint_setting.specifiers.lstrip('=')

                if not spec.contains(version):
                    print('ERROR: Package {!r} is constrained to {} '
                          'which is incompatible with the settings {} '
                          'from {}.'.format(
                              name, version, req, fname))
                    failed = True

                min = [
                    s
                    for s in req.specifiers.split(',')
                    if '>' in s
                ]
                if not min:
                    # No minimum specified. Ignore this and let some
                    # other validation trap the error.
                    continue

                expected = min[0].lstrip('>=')
                if version != expected:
                    print('ERROR: Package {!r} is constrained to {} '
                          'which does not match '
                          'the minimum version specifier {} in {}'.format(
                              name, version, expected, fname))
                    failed = True
    return failed
