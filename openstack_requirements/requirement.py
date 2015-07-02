# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Requirements handling."""

# This module has no IO at all, and none should be added.

import collections

import pkg_resources


# A header for the requirements file(s).
# TODO(lifeless): Remove this once constraints are in use.
_REQS_HEADER = [
    '# The order of packages is significant, because pip processes '
    'them in the order\n',
    '# of appearance. Changing the order has an impact on the overall '
    'integration\n',
    '# process, which may cause wedges in the gate later.\n',
]


Requirement = collections.namedtuple(
    'Requirement', ['package', 'specifiers', 'markers', 'comment'])
Requirements = collections.namedtuple('Requirements', ['reqs'])


def parse(content):
    return to_dict(to_reqs(content))


def parse_line(req_line):
    """Parse a single line of a requirements file.

    requirements files here are a subset of pip requirements files: we don't
    try to parse URL entries, or pip options like -f and -e. Those are not
    permitted in global-requirements.txt. If encountered in a synchronised
    file such as requirements.txt or test-requirements.txt, they are illegal
    but currently preserved as-is.

    They may of course be used by local test configurations, just not
    committed into the OpenStack reference branches.
    """
    end = len(req_line)
    hash_pos = req_line.find('#')
    if hash_pos < 0:
        hash_pos = end
    if '://' in req_line[:hash_pos]:
        # Trigger an early failure before we look for ':'
        pkg_resources.Requirement.parse(req_line)
    semi_pos = req_line.find(';', 0, hash_pos)
    colon_pos = req_line.find(':', 0, hash_pos)
    marker_pos = max(semi_pos, colon_pos)
    if marker_pos < 0:
        marker_pos = hash_pos
    markers = req_line[marker_pos + 1:hash_pos].strip()
    if hash_pos != end:
        comment = req_line[hash_pos:]
    else:
        comment = ''
    req_line = req_line[:marker_pos]

    if req_line:
        parsed = pkg_resources.Requirement.parse(req_line)
        name = parsed.project_name
        specifier = str(parsed.specifier)
    else:
        name = ''
        specifier = ''
    return Requirement(name, specifier, markers, comment)


def to_content(reqs, marker_sep=';', line_prefix='', prefix=True):
    lines = []
    if prefix:
        lines += _REQS_HEADER
    for req in reqs.reqs:
        comment_p = ' ' if req.package else ''
        comment = (comment_p + req.comment if req.comment else '')
        marker = marker_sep + req.markers if req.markers else ''
        package = line_prefix + req.package if req.package else ''
        lines.append('%s%s%s%s\n' % (package, req.specifiers, marker, comment))
    return u''.join(lines)


def to_dict(req_sequence):
    reqs = dict()
    for req, req_line in req_sequence:
        if req is not None:
            reqs.setdefault(req.package.lower(), []).append((req, req_line))
    return reqs


def _pass_through(req_line):
    """Identify unparsable lines."""
    return (req_line.startswith('http://tarballs.openstack.org/') or
            req_line.startswith('-e') or
            req_line.startswith('-f'))


def to_reqs(content):
    for content_line in content.splitlines(True):
        req_line = content_line.strip()
        if _pass_through(req_line):
            yield None, content_line
        else:
            yield parse_line(req_line), content_line
