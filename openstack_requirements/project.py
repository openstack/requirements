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

"""The project abstraction."""

import collections
import errno
import io
import os

from six.moves import configparser

from parsley import makeGrammar

from openstack_requirements import requirement

# PURE logic from here until the IO marker below.


_Comment = collections.namedtuple('Comment', ['line'])
_Extra = collections.namedtuple('Extra', ['name', 'content'])


_extras_grammar = """
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
_extras_compiled = makeGrammar(
    _extras_grammar, {"comment": _Comment, "extra": _Extra})


Error = collections.namedtuple('Error', ['message'])
File = collections.namedtuple('File', ['filename', 'content'])
StdOut = collections.namedtuple('StdOut', ['message'])
Verbose = collections.namedtuple('Verbose', ['message'])


def extras(project):
    """Return a dict of extra-name:content for the extras in setup.cfg."""
    if 'setup.cfg' not in project:
        return {}
    c = configparser.ConfigParser()
    c.read_file(io.StringIO(project['setup.cfg']))
    if not c.has_section('extras'):
        return {}
    return dict(c.items('extras'))


def merge_setup_cfg(old_content, new_extras):
    # This is ugly. All the existing libraries handle setup.cfg's poorly.
    prefix, extras, suffix = _extras_compiled(old_content).ini()
    out_extras = []
    if extras is not None:
        for extra in extras:
            if type(extra) is _Comment:
                out_extras.append(extra)
            elif type(extra) is _Extra:
                if extra.name not in new_extras:
                    out_extras.append(extra)
                    continue
                e = _Extra(
                    extra.name,
                    requirement.to_content(
                        new_extras[extra.name], ':', '  ', False))
                out_extras.append(e)
            else:
                raise TypeError('unknown type %r' % extra)
    if out_extras:
        extras_str = ['[extras]\n']
        for extra in out_extras:
            if type(extra) is _Comment:
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


# IO from here to the end of the file.

def _safe_read(project, filename, output=None):
    if output is None:
        output = project
    try:
        path = os.path.join(project['root'], filename)
        with io.open(path, 'rt', encoding="utf-8") as f:
            output[filename] = f.read()
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise


def read(root):
    """Read into memory the packaging data for the project at root.

    :param root: A directory path.
    :return: A dict representing the project with the following keys:
        - root: The root dir.
        - setup.py: Contents of setup.py.
        - setup.cfg: Contents of setup.cfg.
        - requirements: Dict of requirement file name: contents.
    """
    result = {'root': root}
    _safe_read(result, 'setup.py')
    _safe_read(result, 'setup.cfg')
    requirements = {}
    result['requirements'] = requirements
    target_files = [
        'requirements.txt', 'tools/pip-requires',
        'test-requirements.txt', 'tools/test-requires',
        'doc/requirements.txt',
    ]
    for py_version in (2, 3):
        target_files.append('requirements-py%s.txt' % py_version)
        target_files.append('test-requirements-py%s.txt' % py_version)
    for target_file in target_files:
        _safe_read(result, target_file, output=requirements)
    # Read lower-constraints.txt and ensure the key is always present
    # in case the file is missing.
    result['lower-constraints.txt'] = None
    _safe_read(result, 'lower-constraints.txt')
    return result


def write(project, actions, stdout, verbose, noop=False):
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
            fullname = os.path.join(project['root'], action.filename)
            tmpname = fullname + '.tmp'
            with open(tmpname, 'wt') as f:
                f.write(action.content)
            if os.path.exists(fullname):
                os.remove(fullname)
            os.rename(tmpname, fullname)
        elif type(action) is StdOut:
            stdout.write(action.message)
        elif type(action) is Verbose:
            if verbose:
                stdout.write(u"%s\n" % (action.message,))
        else:
            raise Exception("Invalid action %r" % (action,))
    if error:
        raise Exception("Error occurred processing %s" % (project['root']))
