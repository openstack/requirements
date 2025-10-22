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

import copy
from datetime import datetime
import hashlib
import optparse
import os.path
import shutil
import subprocess
import sys
import tempfile

import fixtures

from openstack_requirements import requirement


SECURITY_WARNING = [
    "# WARNING: OpenStack makes no security guarantees about third-party\n",
    "# dependencies listed here, and does not keep track of any\n",
    "# vulnerabilities they contain. Versions of these dependencies are\n",
    "# frozen at each coordinated release in order to stabilize upstream\n",
    "# testing, and can contain known vulnerabilities. Consumers are\n",
    "# *STRONGLY* encouraged to rely on curated distributions of OpenStack\n",
    "# or manage security patching of dependencies themselves.\n",
    ]


def _parse_freeze(text):
    """Parse a freeze into structured data.

    :param text: The output from a pip freeze command.
    :return: A list of (package, version) tuples.
    """
    result = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('-'):
            raise Exception("Irregular line: %s" % line)
        if line.startswith('#'):
            continue
        if not line:
            continue
        package, version = line.split('==')[:2]
        result.append((package, version))
    return result


def _freeze(requirements, python):
    """Generate a frozen install from requirements.

    A constraints file is the result of installing a set of requirements and
    then freezing the result. We currently special case pip and setuptools
    as pip does, excluding them from the set. We may however want to revisit
    this in future if releases of those things break our gate.

    In principle we should determine this by introspecting all the packages
    transitively, since we need to deal wit environment markers....
    but thats reimplementing a large chunk of pip (and since pip doesn't
    resolve yet, differently too). For now, we take a list of Python
    executables to test under, and then union the results. This is in fact the
    key difference between a constraints file and a requirements file: we're
    not triggering installation, so we can and will list packages that are
    not relevant to e.g. Python3 in the constraints output.

    :param requirements: The path to a requirements file to use when generating
        the constraints.
    :param python: A Python binary to use. E.g. /usr/bin/python3
    :return: A tuple (python_version, list of (package, version)'s)
    """
    output = []
    try:
        version_out = subprocess.check_output(
            [python, "--version"], stderr=subprocess.STDOUT)
        output.append(version_out)
        version_all = version_out.decode('utf-8').split()[1]
        version = '.'.join(version_all.split('.')[:2])
        with fixtures.TempDir() as temp:
            output.append(subprocess.check_output(
                [python, '-m', 'venv', temp.path]))
            pip_bin = os.path.join(temp.path, 'bin', 'pip')
            output.append(subprocess.check_output(
                [pip_bin, 'install', '-U', 'pip', 'setuptools', 'wheel']))
            output.append(subprocess.check_output(
                [pip_bin, 'install', '-r', requirements]))
            freeze = subprocess.check_output(
                [pip_bin, 'freeze'])
            output.append(freeze)
            return (version, _parse_freeze(freeze.decode('utf-8')))
    except Exception as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            output.append(exc.output)
        raise Exception(
            "Failed to generate freeze: %s %s" % (
                b'\n'.join(output).decode('utf-8'),
                exc,
            )
        )
    finally:
        # log job results
        with tempfile.NamedTemporaryFile(
            mode='w+b',
            prefix=datetime.now().strftime(
                'generate-constraints-%Y_%m_%d_%H_%M-'
            ),
            delete=False,
        ) as fh:
            fh.write(b'\n'.join(output))


def _combine_freezes(freezes, denylist=None):
    """Combine multiple freezes into a single structure.

    This deals with the variation between different python versions by
    generating environment markers when different pythons need different
    versions of a dependency.

    :param freezes: A list of (python_version, frozen_requirements) tuples.
    :param denylist: An iterable of package names to exclude. These packages
        won't be included in the output.
    :return: A list of '\n' terminated lines for a requirements file.
    """
    packages = {}  # {package : {version : [py_version]}}
    excludes = frozenset((requirement.canonical_name(s)
                          for s in denylist) if denylist else ())
    reference_versions = []
    for py_version, freeze in freezes:
        if py_version in reference_versions:
            raise Exception("Duplicate python %s" % py_version)

        reference_versions.append(py_version)
        for package, version in freeze:
            packages.setdefault(
                package, {}).setdefault(version, []).append(py_version)

    for package, versions in sorted(packages.items()):
        if package.lower() in excludes:
            continue

        if len(versions) > 1:
            # markers for packages with multiple versions - we use python
            # version ranges for these
            for idx, (version, py_versions) in enumerate(sorted(versions.items())):  # noqa: E501
                if idx == 0:  # lower-bound
                    marker = f"python_version<='{py_versions[-1]}'"
                elif idx + 1 != len(versions):  # intermediate version(s)
                    marker = f"python_version>='{py_versions[0]}',<={py_versions[-1]}"  # noqa: E501
                else:  # upper-bound
                    marker = f"python_version>='{py_versions[0]}'"

                yield f'{package}==={version};{marker}\n'
        elif list(versions.values())[0] != reference_versions:
            # markers for packages with a single version - these are usually
            # version specific so we use strict python versions for these
            for idx, (version, py_versions) in enumerate(sorted(versions.items())):  # noqa: E501
                for py_version in sorted(py_versions):
                    marker = f"python_version=='{py_version}'"
                    yield f'{package}==={version};{marker}\n'
        else:
            # no markers
            yield f'{package}==={list(versions)[0]}\n'


def _clone_versions(freezes, options):
    for freeze_data in freezes:
        versions = [v for v, d in freezes]
        version, freeze = freeze_data
        if version in options.version_map:
            for dst_version in sorted(options.version_map[version]):
                if dst_version not in versions:
                    print("Duplicating %s freeze to %s" %
                          (version, dst_version), file=sys.stderr)
                    freezes.append((dst_version, copy.copy(freeze)))


# -- untested UI glue from here down.

def _validate_options(options):
    """Check that options are valid.

    :param options: The optparse options for this program.
    """
    if not options.pythons:
        raise Exception("No Pythons given - see -p.")
    for python in options.pythons:
        if not shutil.which(python):
            raise Exception(
                "Python %(python)s not found." % dict(python=python))
    if not options.requirements:
        raise Exception("No requirements file specified - see -r.")
    if not os.path.exists(options.requirements):
        raise Exception(
            "Requirements file %(req)s not found."
            % dict(req=options.requirements))
    if options.denylist and not os.path.exists(options.denylist):
        raise Exception(
            "Denylist file %(path)s not found."
            % dict(path=options.denylist))
    version_map = {}
    for map_entry in options.version_map:
        if ':' not in map_entry:
            raise Exception(
                "Invalid version-map entry %(map_entry)s"
                % dict(map_entry=map_entry))
        src, dst = map_entry.split(':')
        version_map.setdefault(src, set())
        version_map[src].add(dst)
    options.version_map = version_map


def _parse_denylist(path):
    """Return the strings from path if it is not None."""
    if path is None:
        return []
    with open(path, 'rt') as f:
        return [line.strip() for line in f]


def _make_sort_key(line):
    """Produce a key that is unlikely to place similar values together.

    We want to avoid sorting all of the oslo libraries together (or
    all of the python-*client libraries) so when we do batch releases
    we do not have merge conflicts in the individual patches updating
    the constraints.

    """
    dep = line.partition('=')[0].encode('utf-8')
    return hashlib.sha1(dep).digest()


def main(argv=None, stdout=None):
    parser = optparse.OptionParser()
    parser.add_option(
        "-p", dest="pythons", action="append",
        help="Specify Python versions to use when generating constraints."
             "e.g. -p /usr/bin/python3")
    parser.add_option(
        "-r", dest="requirements", help="Requirements file to process.")
    parser.add_option(
        "-b", "-d", dest="denylist",
        help="Filename of a list of package names to exclude.")
    parser.add_option(
        "--version-map", dest='version_map', default=[], action='append',
        help=('Add a : separated list of versions to clone.  To \'clone\' '
              'a freeze generated by python3.4 to python3.5 specify 3.4:3.5.  '
              'This is intended as as a way to transition between python '
              'versions when it\'s not possible to have all versions '
              'installed'))
    options, args = parser.parse_args(argv)
    if stdout is None:
        stdout = sys.stdout
    _validate_options(options)
    freezes = [
        _freeze(options.requirements, python) for python in options.pythons]
    _clone_versions(freezes, options)
    denylist = _parse_denylist(options.denylist)
    frozen = [
        *sorted(_combine_freezes(freezes, denylist), key=_make_sort_key)]
    stdout.writelines(SECURITY_WARNING + frozen)
    stdout.flush()
