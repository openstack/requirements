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
import re

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


class Requirement(collections.namedtuple('Requirement',
                                         ['package', 'location', 'specifiers',
                                          'markers', 'comment', 'extras'])):
    def __new__(cls, package, location, specifiers, markers, comment,
                extras=None):
        return super(Requirement, cls).__new__(
            cls, package, location, specifiers, markers, comment,
            frozenset(extras or ()))


Requirements = collections.namedtuple('Requirements', ['reqs'])


url_re = re.compile(
    '^(?P<url>\s*(?:-e\s)?\s*(?:(?:git+)?https|http|file)://[^#]*)'
    '#egg=(?P<name>[-\.\w]+)')


def canonical_name(req_name):
    """Return the canonical form of req_name."""
    return pkg_resources.safe_name(req_name).lower()


def parse(content, permit_urls=False):
    return to_dict(to_reqs(content, permit_urls=permit_urls))


def parse_line(req_line, permit_urls=False):
    """Parse a single line of a requirements file.

    requirements files here are a subset of pip requirements files: we don't
    try to parse URL entries, or pip options like -f and -e. Those are not
    permitted in global-requirements.txt. If encountered in a synchronised
    file such as requirements.txt or test-requirements.txt, they are illegal
    but currently preserved as-is.

    They may of course be used by local test configurations, just not
    committed into the OpenStack reference branches.

    :param permit_urls: If True, urls are parsed into Requirement tuples.
        By default they are not, because they cannot be reflected into
        setuptools kwargs, and thus the default is conservative. When
        urls are permitted, -e *may* be supplied at the start of the line.
    """
    end = len(req_line)
    hash_pos = req_line.find('#')
    if hash_pos < 0:
        hash_pos = end
    # Don't find urls that are in comments.
    if '://' in req_line[:hash_pos]:
        if permit_urls:
            # We accept only a subset of urls here - they have to have an egg
            # name so that we can tell what project its for without doing
            # network access. Egg markers use a fragment, so we need to pull
            # out url from the entire line.
            m = url_re.match(req_line)
            name = m.group('name')
            location = m.group('url')
            parse_start = m.end('name')
            hash_pos = req_line[parse_start:].find('#')
            if hash_pos < 0:
                hash_pos = end
            else:
                hash_pos = hash_pos + parse_start
        else:
            # Trigger an early failure before we look for ':'
            pkg_resources.Requirement.parse(req_line)
    else:
        parse_start = 0
        location = ''
    semi_pos = req_line.find(';', parse_start, hash_pos)
    colon_pos = req_line.find(':', parse_start, hash_pos)
    marker_pos = max(semi_pos, colon_pos)
    if marker_pos < 0:
        marker_pos = hash_pos
    markers = req_line[marker_pos + 1:hash_pos].strip()
    if hash_pos != end:
        comment = req_line[hash_pos:]
    else:
        comment = ''
    req_line = req_line[parse_start:marker_pos]

    extras = ()
    if parse_start:
        # We parsed a url before
        specifier = ''
    elif req_line:
        # Pulled out a requirement
        parsed = pkg_resources.Requirement.parse(req_line)
        name = parsed.project_name
        extras = parsed.extras
        specifier = str(parsed.specifier)
    else:
        # Comments / blank lines etc.
        name = ''
        specifier = ''
    return Requirement(name, location, specifier, markers, comment, extras)


def to_content(reqs, marker_sep=';', line_prefix='', prefix=True):
    lines = []
    if prefix:
        lines += _REQS_HEADER
    for req in reqs.reqs:
        comment_p = ' ' if req.package else ''
        comment = (comment_p + req.comment if req.comment else '')
        marker = marker_sep + req.markers if req.markers else ''
        package = line_prefix + req.package if req.package else ''
        location = req.location + '#egg=' if req.location else ''
        lines.append('%s%s%s%s%s\n' % (
            location, package, req.specifiers, marker, comment))
    return u''.join(lines)


def to_dict(req_sequence):
    reqs = dict()
    for req, req_line in req_sequence:
        if req is not None:
            key = canonical_name(req.package)
            reqs.setdefault(key, []).append((req, req_line))
    return reqs


def _pass_through(req_line, permit_urls=False):
    """Identify unparsable lines."""
    if permit_urls:
        return (req_line.startswith('http://tarballs.openstack.org/') or
                req_line.startswith('-f'))
    else:
        return (req_line.startswith('http://tarballs.openstack.org/') or
                req_line.startswith('-e') or
                req_line.startswith('-f'))


def to_reqs(content, permit_urls=False):
    for content_line in content.splitlines(True):
        req_line = content_line.strip()
        if _pass_through(req_line, permit_urls=permit_urls):
            yield None, content_line
        else:
            yield parse_line(req_line, permit_urls=permit_urls), content_line
