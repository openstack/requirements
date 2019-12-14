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
import distutils.version
import packaging.specifiers
import pkg_resources
import re


# A header for the requirements file(s).
# TODO(lifeless): Remove this once constraints are in use.
_REQS_HEADER = [
    '# The order of packages is significant, because pip processes '
    'them in the order\n',
    '# of appearance. Changing the order has an impact on the overall '
    'integration\n',
    '# process, which may cause wedges in the gate later.\n',
]


def key_specifier(a):
    weight = {'>=': 0, '>': 0,
              '===': 1, '==': 1, '~=': 1, '!=': 1,
              '<': 2, '<=': 2}
    a = a._spec
    return (weight[a[0]], distutils.version.LooseVersion(a[1]))


class Requirement(collections.namedtuple('Requirement',
                                         ['package', 'location', 'specifiers',
                                          'markers', 'comment', 'extras'])):
    def __new__(cls, package, location, specifiers, markers, comment,
                extras=None):
        return super(Requirement, cls).__new__(
            cls, package, location, specifiers, markers, comment,
            frozenset(extras or ()))

    def to_line(self, marker_sep=';', line_prefix='', comment_prefix=' ',
                sort_specifiers=False):
        comment_p = comment_prefix if self.package else ''
        comment = (comment_p + self.comment if self.comment else '')
        marker = marker_sep + self.markers if self.markers else ''
        package = line_prefix + self.package if self.package else ''
        location = self.location + '#egg=' if self.location else ''
        extras = '[%s]' % ",".join(sorted(self.extras)) if self.extras else ''
        specifiers = self.specifiers
        if sort_specifiers:
            _specifiers = packaging.specifiers.SpecifierSet(specifiers)
            _specifiers = ['%s' % s for s in sorted(_specifiers,
                                                    key=key_specifier)]
            specifiers = ','.join(_specifiers)
        return '%s%s%s%s%s%s\n' % (location,
                                   package,
                                   extras,
                                   specifiers,
                                   marker,
                                   comment)


Requirements = collections.namedtuple('Requirements', ['reqs'])


url_re = re.compile(
    r'^(?P<url>\s*(?:-e\s)?\s*(?:(?:[a-z]+\+)?(?:[a-z]+))://[^#]*)'
    r'#egg=(?P<name>[-\.\w]+)')


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
        lines.append(req.to_line(marker_sep, line_prefix))
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


def check_reqs_bounds_policy(global_reqs):
    """Check that the global requirement version specifiers match the policy.

    The policy is defined as
        * There needs to be exactly one lower bound (>=1.2 defined)
        * There can be one or more excludes (!=1.2.1, !=1.2.2)
        * TODO: Clarify (non-) existance of upper caps
    """

    for pkg_requirement in global_reqs.values():
        req = pkg_requirement[0][0]
        if req.package:
            _specifiers = packaging.specifiers.SpecifierSet(req.specifiers)
            lower_bound = set()
            for spec in _specifiers:
                if spec.operator == '>=':
                    lower_bound.add(spec)
            if len(lower_bound):
                yield ('Requirement %s should not include a >= specifier' %
                       req.package)
