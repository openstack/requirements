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

import optparse
import os.path
import sys
import textwrap


from openstack_requirements import requirement


def edit(reqs, name, replacement):
    key = requirement.canonical_name(name)
    if not replacement:
        reqs.pop(key, None)
    else:
        reqs[key] = [
            (requirement.Requirement('', '', '', '', replacement), '')]
    result = []
    for entries in reqs.values():
        for entry, _ in entries:
            result.append(entry)
    return requirement.Requirements(sorted(result))


# -- untested UI glue from here down.


def _validate_options(options, args):
    """Check that options and arguments are valid.

    :param options: The optparse options for this program.
    :param args: The args for this program.
    """
    if len(args) < 2:
        raise Exception("Not enough arguments given")
    if not os.path.exists(args[0]):
        raise Exception(
            "Constraints file %(con)s not found."
            % dict(con=args[0]))


def main(argv=None, stdout=None):
    parser = optparse.OptionParser(
        usage="%prog [options] constraintpath name replacement",
        epilog=textwrap.dedent("""\
            Replaces any entries of "name" in the constraints file with
            "replacement". If "name" is not present, it is added to the end of
            the file. If "replacement" is missing or empty, remove "name" from
            the file.
            """))
    options, args = parser.parse_args(argv)
    if stdout is None:
        stdout = sys.stdout
    _validate_options(options, args)
    args = args + [""]
    content = open(args[0], 'rt').read()
    reqs = requirement.parse(content, permit_urls=True)
    out_reqs = edit(reqs, args[1], args[2])
    out = requirement.to_content(out_reqs, prefix=False)
    with open(args[0] + '.tmp', 'wt') as f:
        f.write(out)
    if os.path.exists(args[0]):
        os.remove(args[0])
    os.rename(args[0] + '.tmp', args[0])
    return 0
