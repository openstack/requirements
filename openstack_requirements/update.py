# Copyright 2012 OpenStack Foundation
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
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

"""
A simple script to update the requirements files from a global set of
allowable requirements.

The script can be called like this:

  $> python update.py ../myproj

Any requirements listed in the target files will have their versions
updated to match the global requirements. Requirements not in the global
files will be dropped.
"""

import collections
import errno
import io
import itertools
import optparse
import os
import os.path
import sys

from parsley import makeGrammar
import pkg_resources
from six.moves import configparser

_setup_py_text = """# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
import setuptools

# In python < 2.7.4, a lazy loading of package `pbr` will break
# setuptools if some other modules registered functions in `atexit`.
# solution from: http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing  # noqa
except ImportError:
    pass

setuptools.setup(
    setup_requires=['pbr'],
    pbr=True)
"""

# A header for the requirements file(s).
# TODO(lifeless): Remove this once constraints are in use.
_REQS_HEADER = [
    '# The order of packages is significant, because pip processes '
    'them in the order\n',
    '# of appearance. Changing the order has an impact on the overall '
    'integration\n',
    '# process, which may cause wedges in the gate later.\n',
]


Comment = collections.namedtuple('Comment', ['line'])
Extra = collections.namedtuple('Extra', ['name', 'content'])


extras_grammar = """
ini = (line*:p extras?:e line*:l final:s) -> (''.join(p), e, ''.join(l+[s]))
line = ~extras <(~'\\n' anything)* '\\n'>
final = <(~'\\n' anything)* >
extras = '[' 'e' 'x' 't' 'r' 'a' 's' ']' '\\n'+ body*:b -> b
body = comment | extra
comment = <'#' (~'\\n' anything)* '\\n'>:c '\\n'* -> comment(c)
extra = name:n ' '* '=' line:l cont*:c '\\n'* -> extra(n, ''.join([l] + c))
name = <(anything:x ?(x not in '\\n \\t='))+>
cont = ' '+ <(~'\\n' anything)* '\\n'>
"""
extras_compiled = makeGrammar(
    extras_grammar, {"comment": Comment, "extra": Extra})


# Pure --
class Change(object):
    def __init__(self, name, old, new):
        self.name = name
        self.old = old.strip()
        self.new = new.strip()

    def __repr__(self):
        return "%-30.30s ->   %s" % (self.old, self.new)


Error = collections.namedtuple('Error', ['message'])
File = collections.namedtuple('File', ['filename', 'content'])
StdOut = collections.namedtuple('StdOut', ['message'])
Verbose = collections.namedtuple('Verbose', ['message'])


Requirement = collections.namedtuple(
    'Requirement', ['package', 'specifiers', 'markers', 'comment'])
Requirements = collections.namedtuple('Requirements', ['reqs'])


def _parse_requirement(req_line):
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


def _pass_through(req_line):
    """Identify unparsable lines."""
    return (req_line.startswith('http://tarballs.openstack.org/') or
            req_line.startswith('-e') or
            req_line.startswith('-f'))


def _check_setup_py(project):
    actions = []
    # If it doesn't have a setup.py, then we don't want to update it
    if 'setup.py' not in project:
        return actions
    # If it doesn't use pbr, we don't want to update it.
    elif 'pbr' not in project['setup.py']:
        return actions
    # We don't update pbr's setup.py because it can't use itself.
    if 'setup.cfg' in project and 'name = pbr' in project['setup.cfg']:
        return actions
    actions.append(Verbose("Syncing setup.py"))
    actions.append(File('setup.py', _setup_py_text))
    return actions


def _sync_requirements_file(
        source_reqs, dest_sequence, dest_label, softupdate, hacking,
        non_std_reqs):
    actions = []
    dest_reqs = _reqs_to_dict(dest_sequence)
    changes = []
    output_requirements = []
    processed_packages = set()

    for req, req_line in dest_sequence:
        # Skip the instructions header
        if req_line in _REQS_HEADER:
            continue
        elif req is None:
            # Unparsable lines.
            output_requirements.append(Requirement('', '', '', req_line))
            continue
        elif not req.package:
            # Comment-only lines
            output_requirements.append(req)
            continue
        elif req.package.lower() in processed_packages:
            continue

        processed_packages.add(req.package.lower())
        # Special cases:
        # projects need to align hacking version on their own time
        if req.package == "hacking" and not hacking:
            output_requirements.append(req)
            continue

        reference = source_reqs.get(req.package.lower())
        if reference:
            actual = dest_reqs.get(req.package.lower())
            for req, ref in itertools.izip_longest(actual, reference):
                if not req:
                    # More in globals
                    changes.append(Change(ref[0].package, '', ref[1]))
                elif not ref:
                    # less in globals
                    changes.append(Change(req[0].package, req[1], ''))
                elif req[0] != ref[0]:
                    # A change on this entry
                    changes.append(Change(req[0].package, req[1], ref[1]))
                if ref:
                    output_requirements.append(ref[0])
        elif softupdate:
            # under softupdate we pass through anything unknown packages,
            # this is intended for ecosystem projects that want to stay in
            # sync with existing requirements, but also add their own above
            # and beyond.
            output_requirements.append(req)
        else:
            # What do we do if we find something unexpected?
            #
            # In the default cause we should die horribly, because
            # the point of global requirements was a single lever
            # to control all the pip installs in the gate.
            #
            # However, we do have other projects using
            # devstack jobs that might have legitimate reasons to
            # override. For those we support NON_STANDARD_REQS=1
            # environment variable to turn this into a warning only.
            # However this drops the unknown requirement.
            actions.append(Error(
                "'%s' is not in global-requirements.txt" % req.package))
    # always print out what we did if we did a thing
    if changes:
        actions.append(StdOut(
            "Version change for: %s\n"
            % ", ".join([x.name for x in changes])))
        actions.append(StdOut("Updated %s:\n" % dest_label))
        for change in changes:
            actions.append(StdOut("    %s\n" % change))
    return actions, Requirements(output_requirements)


def _copy_requires(
        suffix, softupdate, hacking, project, global_reqs, non_std_reqs):
    """Copy requirements files."""
    actions = []
    for source, content in sorted(project['requirements'].items()):
        dest_path = os.path.join(project['root'], source)
        # this is specifically for global-requirements gate jobs so we don't
        # modify the git tree
        if suffix:
            dest_path = "%s.%s" % (dest_path, suffix)
            dest_name = "%s.%s" % (source, suffix)
        else:
            dest_name = source
        dest_sequence = list(_content_to_reqs(content))
        actions.append(Verbose("Syncing %s" % dest_path))
        _actions, reqs = _sync_requirements_file(
            global_reqs, dest_sequence, dest_path, softupdate, hacking,
            non_std_reqs)
        actions.extend(_actions)
        actions.append(File(dest_name, _reqs_to_content(reqs)))
    extras = _project_extras(project)
    output_extras = {}
    for extra, content in sorted(extras.items()):
        dest_name = 'extra-%s' % extra
        dest_path = "%s[%s]" % (project['root'], extra)
        dest_sequence = list(_content_to_reqs(content))
        actions.append(Verbose("Syncing extra [%s]" % extra))
        _actions, reqs = _sync_requirements_file(
            global_reqs, dest_sequence, dest_path, softupdate, hacking,
            non_std_reqs)
        actions.extend(_actions)
        output_extras[extra] = reqs
    dest_path = 'setup.cfg'
    if suffix:
        dest_path = "%s.%s" % (dest_path, suffix)
    actions.append(File(
        dest_path, _merge_setup_cfg(project['setup.cfg'], output_extras)))
    return actions


def _merge_setup_cfg(old_content, new_extras):
    # This is ugly. All the existing libraries handle setup.cfg's poorly.
    prefix, extras, suffix = extras_compiled(old_content).ini()
    out_extras = []
    if extras is not None:
        for extra in extras:
            if type(extra) is Comment:
                out_extras.append(extra)
            elif type(extra) is Extra:
                if extra.name not in new_extras:
                    out_extras.append(extra)
                    continue
                e = Extra(
                    extra.name,
                    _reqs_to_content(
                        new_extras[extra.name], ':', '  ', False))
                out_extras.append(e)
            else:
                raise TypeError('unknown type %r' % extra)
    if out_extras:
        extras_str = ['[extras]\n']
        for extra in out_extras:
            if type(extra) is Comment:
                extras_str.append(extra.line)
            else:
                extras_str.append(extra.name + ' =')
                extras_str.append(extra.content)
        if suffix:
            extras_str.append('\n')
        extras_str = ''.join(extras_str)
    else:
        extras_str = ''
    return prefix + extras_str + suffix


def _project_extras(project):
    """Return a dict of extra-name:content for the extras in setup.cfg."""
    c = configparser.SafeConfigParser()
    c.readfp(io.StringIO(project['setup.cfg']))
    if not c.has_section('extras'):
        return dict()
    return dict(c.items('extras'))


def _reqs_to_content(reqs, marker_sep=';', line_prefix='', prefix=True):
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


def _process_project(
        project, global_reqs, suffix, softupdate, hacking, non_std_reqs):
    """Project a project.

    :return: The actions to take as a result.
    """
    actions = _copy_requires(
        suffix, softupdate, hacking, project, global_reqs, non_std_reqs)
    actions.extend(_check_setup_py(project))
    return actions


def _content_to_reqs(content):
    for content_line in content.splitlines(True):
        req_line = content_line.strip()
        if _pass_through(req_line):
            yield None, content_line
        else:
            yield _parse_requirement(req_line), content_line


def _parse_reqs(content):
    return _reqs_to_dict(_content_to_reqs(content))


def _reqs_to_dict(req_sequence):
    reqs = dict()
    for req, req_line in req_sequence:
        if req is not None:
            reqs.setdefault(req.package.lower(), []).append((req, req_line))
    return reqs


# IO --
def _safe_read(project, filename, output=None):
    if output is None:
        output = project
    try:
        path = project['root'] + '/' + filename
        with io.open(path, 'rt', encoding="utf-8") as f:
            output[filename] = f.read()
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise


def _read_project(root):
    result = {'root': root}
    _safe_read(result, 'setup.py')
    _safe_read(result, 'setup.cfg')
    requirements = {}
    result['requirements'] = requirements
    target_files = [
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
    ]
    for py_version in (2, 3):
        target_files.append('requirements-py%s.txt' % py_version)
        target_files.append('test-requirements-py%s.txt' % py_version)
    for target_file in target_files:
        _safe_read(result, target_file, output=requirements)
    return result


def _write_project(project, actions, stdout, verbose, noop=False):
    """Write actions into project.

    :param project: A project metadata dict.
    :param actions: A list of action tuples - File or Verbose - that describe
        what actions are to be taken.
        Error objects write a message to stdout and trigger an exception at
            the end of _write_project.
        File objects describe a file to have content placed in it.
        StdOut objects describe a message to write to stdout.
        Verbose objects will write a message to stdout when verbose is True.
    :param stdout: Where to write content for stdout.
    :param verbose: If True Verbose actions will be written to stdout.
    :param noop: If True nothing will be written to disk.
    :return None:
    :raises IOError: If the IO operations fail, IOError is raised. If this
        happens some actions may have been applied and others not.
    """
    error = False
    for action in actions:
        if type(action) is Error:
            error = True
            stdout.write(action.message + '\n')
        elif type(action) is File:
            if noop:
                continue
            fullname = project['root'] + '/' + action.filename
            tmpname = fullname + '.tmp'
            with open(tmpname, 'wt') as f:
                f.write(action.content)
            os.rename(tmpname, fullname)
        elif type(action) is StdOut:
            stdout.write(action.message)
        elif type(action) is Verbose:
            if verbose:
                stdout.write(u"%s\n" % (action.message,))
        else:
            raise Exception("Invalid action %r" % (action,))
    if error:
        raise Exception("Error occured processing %s" % (project['root']))


def main(argv=None, stdout=None, _worker=None):
    parser = optparse.OptionParser()
    parser.add_option("-o", "--output-suffix", dest="suffix", default="",
                      help="output suffix for updated files (i.e. .global)")
    parser.add_option("-s", "--soft-update", dest="softupdate",
                      action="store_true",
                      help="Pass through extra requirements without warning.")
    parser.add_option("-H", "--hacking", dest="hacking",
                      action="store_true",
                      help="Include the hacking project.")
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true",
                      help="Add further verbosity to output")
    parser.add_option("--source", dest="source", default=".",
                      help="Dir where global-requirements.txt is located.")
    options, args = parser.parse_args(argv)
    if len(args) != 1:
        print("Must specify directory to update")
        raise Exception("Must specify one and only one directory to update.")
    if stdout is None:
        stdout = sys.stdout
    if _worker is None:
        _worker = _do_main
    non_std_reqs = os.getenv('NON_STANDARD_REQS', '0') == '1'
    _worker(
        args[0], options.source, options.suffix, options.softupdate,
        options.hacking, stdout, options.verbose, non_std_reqs)


def _do_main(
        root, source, suffix, softupdate, hacking, stdout, verbose,
        non_std_reqs):
    """No options or environment variable access from here on in."""
    project = _read_project(root)
    global_req_content = open(
        os.path.join(source, 'global-requirements.txt'), 'rt').read()
    global_reqs = _parse_reqs(global_req_content)
    actions = _process_project(
        project, global_reqs, suffix, softupdate, hacking, non_std_reqs)
    _write_project(project, actions, stdout=stdout, verbose=verbose)


if __name__ == "__main__":
    main()
